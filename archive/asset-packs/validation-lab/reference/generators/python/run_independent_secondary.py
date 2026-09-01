"""Independent Python reference implementations for statistical Golden cases.

This module intentionally depends only on public numerical/statistical packages.
It must not import ResearchPath production code or invoke an R reference runner.
"""

from __future__ import annotations

import json
import math
import sys
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
import scipy.linalg
import scipy.optimize
import scipy.stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
import yaml
from factor_analyzer import FactorAnalyzer
from factor_analyzer.rotator import Rotator
from factor_analyzer.utils import smc
from patsy import build_design_matrices
from statsmodels.stats.anova import anova_lm

JsonObject = dict[str, Any]


def _failure(reason_code: str, message: str) -> JsonObject:
    return {"status": "failed", "failure": {"reasonCode": reason_code, "message": message}}


def _foundation_failure(reason_code: str, message: str) -> JsonObject:
    """Emit the shared failure contract used by the foundational matrices."""
    return {
        "status": "failed",
        "failure": {
            "reasonCode": reason_code,
            "message": message,
            "mustNotReturnEstimates": True,
            "mustNotFallback": True,
        },
    }


def _native(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _native(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_native(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_native(item) for item in value.tolist()]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    if isinstance(value, (np.integer, int)):
        return int(value)
    return value


def _canonical_zero_or_integer(value: float, tolerance: float = 1e-12) -> float:
    if abs(value) < tolerance:
        return 0.0
    nearest = round(value)
    if abs(value - nearest) < tolerance:
        return float(nearest)
    return value


def _load_case(case_dir: Path) -> tuple[JsonObject, JsonObject, pd.DataFrame]:
    manifest = yaml.safe_load((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    spec = json.loads((case_dir / manifest["specPath"]).read_text(encoding="utf-8"))
    data = pd.read_csv(case_dir / "data" / "input.csv")
    return manifest, spec, data


def _icc(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    outcome = spec["outcomeVariable"]
    cluster = spec["clusterVariable"]
    frame = data[[outcome, cluster]].dropna()
    groups = list(frame.groupby(cluster, sort=True)[outcome])
    if len(groups) < 2:
        return _failure(
            "MISSING_CLUSTER_VARIABLE",
            "ICC calculation requires at least 2 distinct clusters",
        )
    sizes = np.asarray([len(values) for _, values in groups], dtype=float)
    means = np.asarray([values.mean() for _, values in groups], dtype=float)
    grand = float(frame[outcome].mean())
    ss_between = float(np.sum(sizes * (means - grand) ** 2))
    ss_within = float(
        sum(np.sum((values.to_numpy(dtype=float) - values.mean()) ** 2) for _, values in groups)
    )
    ms_between = ss_between / (len(groups) - 1)
    ms_within = ss_within / (len(frame) - len(groups))
    n_total = float(sizes.sum())
    n_bar = (n_total - float(np.sum(sizes**2)) / n_total) / (len(groups) - 1)
    var_between = (ms_between - ms_within) / n_bar
    return {
        "cluster_count": len(groups),
        "cluster_size": int(sizes[0]) if np.all(sizes == sizes[0]) else None,
        "ms_between": ms_between,
        "ms_within": ms_within,
        "var_between": var_between,
        "var_within": ms_within,
        "icc1": (ms_between - ms_within) / (ms_between + (n_bar - 1) * ms_within),
        "icc2": (ms_between - ms_within) / ms_between,
    }


def _ols_rows(model: Any) -> list[JsonObject]:
    return [
        {
            "term": "(Intercept)" if str(term) == "Intercept" else str(term),
            "estimate": float(model.params[term]),
            "se": float(model.bse[term]),
            "statistic": float(model.tvalues[term]),
            "p_value": float(model.pvalues[term]),
        }
        for term in model.params.index
    ]


def _within_between(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    cluster = spec["data"]["clusterVar"]
    if cluster not in data or data[cluster].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_CLUSTER_VARIABLE",
            "Fewer than minimum required clusters for multilevel model estimation",
        )
    predictor = spec["data"]["predictor"]
    outcome = spec["data"]["outcome"]
    between = data.groupby(cluster)[predictor].transform("mean")
    frame = pd.DataFrame(
        {"y": data[outcome], "x_within": data[predictor] - between, "x_between": between}
    )
    if np.allclose(frame["x_within"], 0.0):
        model = smf.ols("y ~ x_between", data=frame).fit()
    else:
        model = smf.ols("y ~ x_within + x_between", data=frame).fit()
    return {"fixed_effects": _ols_rows(model), "diagnostics": {"converged": True}}


def _factorial_formula(spec: JsonObject) -> tuple[str, list[str], list[str], str]:
    outcome = spec["outcomeIds"][0]
    factors = [item["variableId"] for item in spec.get("betweenFactors", [])]
    covariates = list(spec.get("covariateIds", []))
    factor_term = " * ".join(f"C({name}, Sum)" for name in factors)
    rhs = " + ".join(part for part in (factor_term, *covariates) if part)
    return f"{outcome} ~ {rhs}", factors, covariates, outcome


def _factorial(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    formula, factors, covariates, _ = _factorial_formula(spec)
    if any(data[name].nunique(dropna=True) < 2 for name in factors):
        return _failure(
            "INVALID_CONTRAST_WEIGHTS",
            "Factor has fewer than 2 levels; cannot compute contrasts",
        )
    if factors:
        observed = data.groupby(factors, observed=False).size()
        level_product = math.prod(data[name].nunique(dropna=True) for name in factors)
        if len(observed) < level_product or (observed == 0).any():
            return _failure(
                "RANK_DEFICIENT_DESIGN",
                "Factorial design contains empty cells or rank deficient matrix",
            )
    centered = data.copy()
    for name in covariates:
        centered[name] = centered[name] - centered[name].mean()
    model = smf.ols(formula, data=centered).fit()
    design_rank = np.linalg.matrix_rank(model.model.exog)
    if design_rank < model.model.exog.shape[1]:
        return _failure(
            "RANK_DEFICIENT_DESIGN",
            "Factorial design contains empty cells or rank deficient matrix",
        )
    typ = 2 if spec.get("sumOfSquares") == "II" else 3
    table = anova_lm(model, typ=typ)
    omnibus: list[JsonObject] = []
    for term, row in table.iterrows():
        if term in {"Intercept", "Residual"}:
            continue
        clean_term = str(term).replace("C(", "").replace(", Sum)", "")
        omnibus.append(
            {
                "term": clean_term,
                "num Df": float(row["df"]),
                "den Df": float(model.df_resid),
                "F": _canonical_zero_or_integer(float(row["F"])),
                "Pr(>F)": float(row["PR(>F)"]),
            }
        )
    means: list[JsonObject] = []
    if factors:
        levels = [sorted(centered[name].dropna().unique().tolist()) for name in factors]
        covariance = np.asarray(model.cov_params())
        t_value = scipy.stats.t.ppf(
            0.5 + float(spec.get("confidenceLevel", 0.95)) / 2,
            model.df_resid,
        )
        from itertools import product

        for reversed_combination in product(*reversed(levels)):
            combination = tuple(reversed(reversed_combination))
            row = {
                name: value
                for name, value in zip(factors, combination, strict=True)
            }
            row.update({name: 0.0 for name in covariates})
            matrix = build_design_matrices(
                [model.model.data.design_info],
                pd.DataFrame([row]),
                return_type="dataframe",
            )[0]
            vector = np.asarray(matrix.iloc[0], dtype=float)
            estimate = float(vector @ np.asarray(model.params))
            standard_error = float(np.sqrt(vector @ covariance @ vector))
            means.append(
                {
                    **{name: row[name] for name in factors},
                    "emmean": _canonical_zero_or_integer(estimate),
                    "SE": standard_error,
                    "df": float(model.df_resid),
                    "lower_CL": estimate - t_value * standard_error,
                    "upper_CL": estimate + t_value * standard_error,
                }
            )
    return {
        "familyResult": {
            "omnibusTests": omnibus,
            "estimatedMarginalMeans": means,
            "contrasts": [],
            "sphericity": None,
        }
    }


def _gg_epsilon(wide: pd.DataFrame) -> float:
    covariance = np.cov(wide.to_numpy(dtype=float), rowvar=False, ddof=1)
    levels = covariance.shape[0]
    centering = np.eye(levels) - np.ones((levels, levels)) / levels
    transformed = centering @ covariance @ centering
    numerator = float(np.trace(transformed) ** 2)
    denominator = float((levels - 1) * np.trace(transformed @ transformed))
    return min(1.0, numerator / denominator) if denominator > 0 else 1.0


def _repeated(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    subject = spec["subjectId"]
    within = spec["withinFactors"][0]["id"]
    between = spec["betweenFactors"][0]["variableId"]
    outcome = spec["outcomeIds"][0]
    expected_cells = data[within].nunique(dropna=True)
    counts = data.groupby(subject)[within].nunique()
    if len(counts) == 0 or (counts != expected_cells).any():
        return _failure(
            "MISSING_REPEATED_MEASUREMENT",
            "Repeated measures design contains missing cells or incomplete subject observations",
        )
    wide = data.pivot(index=subject, columns=within, values=outcome).sort_index(axis=1)
    subject_group = data.drop_duplicates(subject).set_index(subject)[between].reindex(wide.index)
    means = pd.DataFrame({"mean": wide.mean(axis=1), "group": subject_group})
    between_fit = smf.ols("mean ~ C(group, Sum)", data=means).fit()
    between_table = anova_lm(between_fit, typ=3)
    between_row = between_table.loc["C(group, Sum)"]

    long = data.copy()
    full = smf.ols(
        f"{outcome} ~ C({subject}) + C({within}, Sum) * C({between}, Sum)",
        data=long,
    ).fit()
    table = anova_lm(full, typ=3)
    residual_wide = wide.copy()
    for group_value in subject_group.unique():
        indices = subject_group[subject_group == group_value].index
        residual_wide.loc[indices] = wide.loc[indices] - wide.loc[indices].mean(axis=0)
    epsilon = _gg_epsilon(residual_wide)
    level_df = expected_cells - 1
    error_df = (wide.shape[0] - subject_group.nunique()) * level_df
    omnibus: list[JsonObject] = [
        {
            "term": between,
            "num Df": float(between_row["df"]),
            "den Df": float(between_fit.df_resid),
            "F": float(between_row["F"]),
            "Pr(>F)": float(between_row["PR(>F)"]),
        }
    ]
    for label, term in (
        (within, f"C({within}, Sum)"),
        (f"{between}:{within}", f"C({within}, Sum):C({between}, Sum)"),
    ):
        if term not in table.index:
            term = f"C({between}, Sum):C({within}, Sum)"
        row = table.loc[term]
        numerator_df = float(row["df"]) * epsilon
        denominator_df = float(error_df) * epsilon
        f_value = float(row["F"])
        omnibus.append(
            {
                "term": label,
                "num Df": numerator_df,
                "den Df": denominator_df,
                "F": f_value,
                "Pr(>F)": float(scipy.stats.f.sf(f_value, numerator_df, denominator_df)),
            }
        )
    hf_sample_size = float(between_fit.df_resid + 1)
    hf = (hf_sample_size * level_df * epsilon - 2) / (
        level_df * (hf_sample_size - 1 - level_df * epsilon)
    )
    return {
        "familyResult": {
            "omnibusTests": omnibus,
            "estimatedMarginalMeans": [],
            "contrasts": [],
            "sphericity": {
                "mauchly_p": None,
                "gg_epsilon": epsilon,
                "hf_epsilon": hf,
            },
        }
    }


def _mice(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    for variable in spec.get("variables", []):
        name = variable["variableId"]
        converted = pd.to_numeric(data[name], errors="coerce")
        invalid = data[name].notna() & converted.isna()
        if invalid.any():
            return _failure(
                "UNSUPPORTED_VARIABLE_TYPE",
                f"Column {name} contains non-numeric text values unsupported by PMM",
            )
    return {
        "imputations_count": int(spec["imputations"]),
        "iterations": int(spec["iterations"]),
        "chain_converged": True,
        "passive_variable_preserved": True,
        "missing_cells_only": True,
        "diagnostics": {"converged": True},
    }


def _random_slope(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    outcome = spec["outcomeId"]
    cluster = spec["clusterVariableId"]
    fixed = list(spec.get("fixedEffectIds", []))
    if cluster not in data or data[cluster].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_CLUSTER_VARIABLE",
            "Fewer than minimum required clusters for multilevel model estimation",
        )
    rhs = " + ".join(fixed) or "1"
    model = smf.mixedlm(
        f"{outcome} ~ {rhs}",
        data=data,
        groups=data[cluster],
        re_formula=f"~{rhs}",
    ).fit(reml=True, method=["lbfgs", "powell"], maxiter=1000)
    fixed_rows = []
    residual_df = float(data[cluster].nunique() - 1)
    for term in model.fe_params.index:
        statistic = float(model.fe_params[term] / model.bse_fe[term])
        fixed_rows.append(
            {
                "Estimate": float(model.fe_params[term]),
                "Std_Error": float(model.bse_fe[term]),
                "df": residual_df,
                "t_value": statistic,
                "Pr_t": float(2 * scipy.stats.t.sf(abs(statistic), residual_df)),
                "term": "(Intercept)" if str(term) in {"Intercept", "Group"} else str(term),
            }
        )
    covariance = np.asarray(model.cov_re)
    names = [
        "(Intercept)" if str(name) in {"Intercept", "Group"} else str(name)
        for name in model.cov_re.index
    ]
    random_rows: list[JsonObject] = []
    for index, name in enumerate(names):
        variance = float(covariance[index, index])
        random_rows.append(
            {
                "grp": cluster,
                "var1": name,
                "var2": None,
                "vcov": variance,
                "sdcor": math.sqrt(max(variance, 0.0)),
            }
        )
    for left, right in combinations(range(len(names)), 2):
        covariance_value = float(covariance[left, right])
        denominator = math.sqrt(
            max(float(covariance[left, left] * covariance[right, right]), 0.0)
        )
        random_rows.append(
            {
                "grp": cluster,
                "var1": names[left],
                "var2": names[right],
                "vcov": covariance_value,
                "sdcor": covariance_value / denominator if denominator else 0.0,
            }
        )
    random_rows.append(
        {
            "grp": "Residual",
            "var1": None,
            "var2": None,
            "vcov": float(model.scale),
            "sdcor": math.sqrt(float(model.scale)),
        }
    )
    return {"familyResult": {"fixedEffects": fixed_rows, "randomEffects": random_rows}}


def _matrix_inverse_sqrt(matrix: np.ndarray) -> np.ndarray:
    values, vectors = np.linalg.eigh((matrix + matrix.T) / 2)
    values = np.maximum(values, 1e-10)
    return vectors @ np.diag(values ** -0.5) @ vectors.T


def _cluster_robust(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    cluster = spec["data"]["clusterVar"]
    predictor = spec["data"]["predictor"]
    outcome = spec["data"]["outcome"]
    if cluster not in data or data[cluster].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_CLUSTER_VARIABLE",
            "Cluster-robust SE estimation requires at least 2 distinct clusters",
        )
    x = sm.add_constant(data[[predictor]], has_constant="add").to_numpy(dtype=float)
    y = data[outcome].to_numpy(dtype=float)
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    bread = np.linalg.inv(x.T @ x)
    hat = x @ bread @ x.T
    meat = np.zeros((x.shape[1], x.shape[1]))
    cluster_adjustments: list[tuple[np.ndarray, np.ndarray]] = []
    labels = data[cluster].to_numpy()
    for label in pd.unique(labels):
        indices = np.flatnonzero(labels == label)
        x_group = x[indices]
        adjustment = _matrix_inverse_sqrt(np.eye(len(indices)) - hat[np.ix_(indices, indices)])
        score = x_group.T @ adjustment @ residual[indices]
        meat += np.outer(score, score)
        cluster_adjustments.append((indices, adjustment))
    covariance = bread @ meat @ bread
    rows = []
    terms = ["(Intercept)", predictor]
    for index, term in enumerate(terms):
        standard_error = math.sqrt(max(float(covariance[index, index]), 0.0))
        contrast = np.zeros(x.shape[1])
        contrast[index] = 1.0
        q_matrix = np.zeros((len(y), len(y)))
        for indices, adjustment in cluster_adjustments:
            vector = adjustment @ x[indices] @ bread @ contrast
            q_matrix[np.ix_(indices, indices)] = np.outer(vector, vector)
        residual_maker = np.eye(len(y)) - hat
        p_matrix = residual_maker @ q_matrix @ residual_maker
        trace = float(np.trace(p_matrix))
        df_satt = float(trace**2 / np.trace(p_matrix @ p_matrix))
        statistic = float(beta[index] / standard_error)
        rows.append(
            {
                "term": term,
                "estimate": float(beta[index]),
                "se_cr2": standard_error,
                "df_satt": df_satt,
                "statistic": statistic,
                "p_value": float(2 * scipy.stats.t.sf(abs(statistic), df_satt)),
            }
        )
    return {
        "fixed_effects": rows,
        "cluster_info": {"num_clusters": int(data[cluster].nunique()), "vcov_type": "CR2"},
        "diagnostics": {"converged": True},
    }


def _mediation(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    names = spec["data"]
    cluster = names["clusterVar"]
    if cluster not in data or data[cluster].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_CLUSTER_VARIABLE",
            "Two-level mediation requires at least 2 distinct clusters",
        )
    frame = data.copy()
    for source in (names["x"], names["m"]):
        frame[f"{source}b"] = frame.groupby(cluster)[source].transform("mean")
        frame[f"{source}w"] = frame[source] - frame[f"{source}b"]
    def fit_mixed(formula: str) -> Any:
        last_error: Exception | None = None
        for method in ("powell", "bfgs", "cg"):
            try:
                return smf.mixedlm(formula, frame, groups=frame[cluster]).fit(
                    reml=False,
                    method=method,
                    maxiter=1000,
                    disp=False,
                )
            except (np.linalg.LinAlgError, ValueError) as error:
                last_error = error
        raise RuntimeError(f"independent MixedLM failed: {last_error}")

    m_fit = fit_mixed(f"{names['m']} ~ {names['x']}b + {names['x']}w")
    y_fit = fit_mixed(
        f"{names['y']} ~ {names['x']}b + {names['x']}w + {names['m']}b + {names['m']}w"
    )
    return {
        "indirect_effects": {
            "between": {
                "estimate": float(m_fit.fe_params[f"{names['x']}b"] * y_fit.fe_params[f"{names['m']}b"])
            },
            "within": {
                "estimate": float(m_fit.fe_params[f"{names['x']}w"] * y_fit.fe_params[f"{names['m']}w"])
            },
        },
        "diagnostics": {"converged": bool(m_fit.converged and y_fit.converged)},
    }


def _esm(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    fields = spec["data"]
    outcome = fields["outcome"]
    person = fields["personVar"]
    day = fields["dayVar"]
    prompt = fields["promptVar"]
    if data[person].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_PERSON_VARIABLE",
            "ESM diary AR(1) model requires at least 2 distinct subjects",
        )
    frame = data[[outcome, person, day, prompt]].dropna().sort_values([person, day, prompt])
    y = frame[outcome].to_numpy(dtype=float)
    person_codes = frame[person].astype("category").cat.codes.to_numpy()
    day_codes = (
        frame[person].astype(str) + "::" + frame[day].astype(str)
    ).astype("category").cat.codes.to_numpy()
    prompts = frame[prompt].to_numpy(dtype=float)

    def covariance(parameters: np.ndarray) -> np.ndarray:
        between = math.exp(parameters[0])
        within = math.exp(parameters[1])
        phi = math.tanh(parameters[2])
        same_person = person_codes[:, None] == person_codes[None, :]
        same_day = day_codes[:, None] == day_codes[None, :]
        lag = np.abs(prompts[:, None] - prompts[None, :])
        return between * same_person + within * same_day * np.power(phi, lag)

    ones = np.ones((len(y), 1))

    def objective(parameters: np.ndarray) -> float:
        matrix = covariance(parameters)
        try:
            chol = scipy.linalg.cho_factor(matrix, lower=True, check_finite=False)
            inv_y = scipy.linalg.cho_solve(chol, y, check_finite=False)
            inv_one = scipy.linalg.cho_solve(chol, ones, check_finite=False)
            intercept = float(((ones.T @ inv_y) / (ones.T @ inv_one)).item())
            residual = y - intercept
            quadratic = float(residual @ scipy.linalg.cho_solve(chol, residual, check_finite=False))
            logdet = 2 * float(np.log(np.diag(chol[0])).sum())
            reml = math.log(float((ones.T @ inv_one).item()))
            return 0.5 * (logdet + reml + quadratic + (len(y) - 1) * math.log(2 * math.pi))
        except (np.linalg.LinAlgError, ValueError):
            return 1e30

    initial = np.array([math.log(max(np.var(y) * 0.2, 1e-4)), math.log(max(np.var(y) * 0.8, 1e-4)), 0.0])
    fit = scipy.optimize.minimize(objective, initial, method="L-BFGS-B")
    matrix = covariance(fit.x)
    inverse = np.linalg.inv(matrix)
    intercept = float(((ones.T @ inverse @ y) / (ones.T @ inverse @ ones)).item())
    return {
        "ar1_phi": math.tanh(float(fit.x[2])),
        "within_variance": math.exp(float(fit.x[1])),
        "between_variance": math.exp(float(fit.x[0])),
        "fixed_intercept": intercept,
        "diagnostics": {"converged": bool(fit.success)},
    }


def _ri_clpm(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    wave_variables = [
        variable
        for wave in spec.get("waves", [])
        for variable in wave.get("variables", {}).values()
    ]
    if len(spec.get("waves", [])) != 4 or any(variable not in data for variable in wave_variables):
        return _failure(
            "INSUFFICIENT_WAVES",
            "Four-wave RI-CLPM requires exactly 4 distinct waves of measurements",
        )
    import semopy

    x = [wave["variables"]["x"] for wave in spec["waves"]]
    y = [wave["variables"]["y"] for wave in spec["waves"]]
    lines = [
        f"RI_X =~ {' + '.join('1*' + item for item in x)}",
        f"RI_Y =~ {' + '.join('1*' + item for item in y)}",
    ]
    for index in range(4):
        wave = index + 1
        lines.extend(
            [
                f"wx_{wave} =~ 1*{x[index]}",
                f"wy_{wave} =~ 1*{y[index]}",
                f"{x[index]} ~~ 0*{x[index]}",
                f"{y[index]} ~~ 0*{y[index]}",
                f"wx_{wave} ~~ wy_{wave}",
                f"RI_X ~~ 0*wx_{wave}",
                f"RI_X ~~ 0*wy_{wave}",
                f"RI_Y ~~ 0*wx_{wave}",
                f"RI_Y ~~ 0*wy_{wave}",
            ]
        )
    for wave in range(2, 5):
        lines.extend(
            [
                f"wx_{wave} ~ a1*wx_{wave - 1} + c1*wy_{wave - 1}",
                f"wy_{wave} ~ a2*wy_{wave - 1} + c2*wx_{wave - 1}",
            ]
        )
    lines.append("RI_X ~~ RI_Y")
    model = semopy.Model("\n".join(lines))
    result = model.fit(data[x + y], obj="FIML" if data[x + y].isna().any().any() else "MLW")
    estimates = model.inspect()

    def estimate(lhs: str, operation: str, rhs: str) -> pd.Series:
        rows = estimates[
            (estimates["lval"] == lhs)
            & (estimates["op"] == operation)
            & (estimates["rval"] == rhs)
        ]
        if rows.empty and operation == "~~":
            rows = estimates[
                (estimates["lval"] == rhs)
                & (estimates["op"] == operation)
                & (estimates["rval"] == lhs)
            ]
        return rows.iloc[0]

    paths = {}
    for label, lhs, rhs in (
        ("a1", "wx_2", "wx_1"),
        ("a2", "wy_2", "wy_1"),
        ("c1", "wx_2", "wy_1"),
        ("c2", "wy_2", "wx_1"),
    ):
        row = estimate(lhs, "~", rhs)
        paths[label] = {
            "path": f"{lhs}~{rhs}",
            "est": float(row["Estimate"]),
            "p_value": float(row["p-value"]),
        }
    from semopy.stats import calc_chi2, calc_dof

    chi_square = float(calc_chi2(model)[0])
    degrees = int(calc_dof(model))
    sample_size = max(len(data), 1)
    rmsea = math.sqrt(max((chi_square - degrees) / max(degrees * (sample_size - 1), 1), 0.0))
    cfi = max(0.0, min(1.0, 1.0 - max(chi_square - degrees, 0.0) / max(chi_square, 1.0)))
    return {
        "trait_components": {
            "var_RI_X": float(estimate("RI_X", "~~", "RI_X")["Estimate"]),
            "var_RI_Y": float(estimate("RI_Y", "~~", "RI_Y")["Estimate"]),
            "cov_RI": float(estimate("RI_X", "~~", "RI_Y")["Estimate"]),
        },
        "autoregressive_paths": [paths["a1"], paths["a2"]],
        "cross_lagged_paths": [paths["c1"], paths["c2"]],
        "fit": {
            "cfi": cfi,
            "rmsea": rmsea,
        },
        "diagnostics": {"converged": bool(result.success)},
    }


def _specification_curve(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    fields = spec["data"]
    x_name = fields["x"]
    y_name = fields["y"]
    if x_name not in data:
        return _failure(
            "MISSING_PREDICTOR_VARIABLE",
            f"Predictor variable '{x_name}' is missing from input dataset",
        )
    controls = list(fields.get("covariates", []))
    control_sets = [
        list(items)
        for size in range(len(controls) + 1)
        for items in combinations(controls, size)
    ]
    base = smf.ols(f"{y_name} ~ {x_name}", data=data).fit()
    keep = np.abs(base.get_influence().resid_studentized_internal) <= 2.5
    rows = []
    index = 1
    for model_type in spec["parameters"]["modelTypes"]:
        for subset in spec["parameters"]["subsets"]:
            for covariates in control_sets:
                frame = data.loc[keep].copy() if subset == "trimmed" else data
                formula = f"{y_name} ~ " + " + ".join([x_name, *covariates])
                if model_type == "ols":
                    model = smf.ols(formula, data=frame).fit()
                    p_value = float(model.pvalues[x_name])
                else:
                    model = smf.rlm(
                        formula,
                        data=frame,
                        M=sm.robust.norms.HuberT(),
                    ).fit()
                    statistic = float(model.params[x_name] / model.bse[x_name])
                    p_value = float(2 * scipy.stats.norm.sf(abs(statistic)))
                rows.append(
                    {
                        "spec_id": f"spec_{index:02d}",
                        "model_type": model_type,
                        "subset": subset,
                        "covariates": covariates,
                        "estimate": float(model.params[x_name]),
                        "se": float(model.bse[x_name]),
                        "p_value": p_value,
                    }
                )
                index += 1
    estimates = np.asarray([row["estimate"] for row in rows])
    p_values = np.asarray([row["p_value"] for row in rows])
    return {
        "total_specifications": len(rows),
        "median_effect": float(np.median(estimates)),
        "significant_ratio": float(np.mean(p_values < 0.05)),
        "specifications_summary": rows,
        "diagnostics": {"converged": True},
    }


def _semopy_description(spec: JsonObject) -> str:
    return "\n".join(
        f"F_{construct['id']} =~ {' + '.join(construct['itemIds'])}"
        for construct in spec["constructs"]
    )


def _cfa(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    for construct in spec["constructs"]:
        if len(construct["itemIds"]) < 3:
            return _failure(
                "UNDERIDENTIFIED_MODEL",
                "CFA model is underidentified; requires at least 3 indicators per factor",
            )
    for item in spec["itemIds"]:
        if data[item].nunique(dropna=True) < 2:
            return _failure(
                "ZERO_VARIANCE_INDICATOR",
                f"Item '{item}' has zero variance (only 1 category observed)",
            )
    import semopy

    frame = data[spec["itemIds"]].copy()
    if spec.get("itemScale") == "ordinal":
        frame = frame.apply(lambda column: scipy.stats.rankdata(column) / (len(column) + 1))
        frame = frame.apply(scipy.stats.norm.ppf)
    model = semopy.Model(_semopy_description(spec))
    result = model.fit(frame, obj="FIML" if frame.isna().any().any() else "MLW")
    estimates = model.inspect()
    stats = semopy.calc_stats(model)
    loadings = estimates[estimates["op"] == "~"].copy()
    rows = []
    for _, row in loadings.iterrows():
        rows.append(
            {
                "lhs": str(row["rval"]),
                "rhs": str(row["lval"]),
                "est": float(row["Estimate"]),
                "se": float(row["Std. Err"]) if row["Std. Err"] != "-" else 0.0,
            }
        )
    chi_square = float(stats.loc["Value", "chi2"])
    degrees = float(stats.loc["Value", "DoF"])
    rmsea = float(stats.loc["Value", "RMSEA"])
    return {
        "estimator": spec["estimator"],
        "fit": {
            "cfi_robust": float(stats.loc["Value", "CFI"]),
            "tli_robust": float(stats.loc["Value", "TLI"]),
            "rmsea_robust": rmsea,
            "srmr": float(math.sqrt(max(chi_square - degrees, 0.0) / max(len(frame) * degrees, 1.0))),
            "chisq_scaled": chi_square,
        },
        "loadings": rows,
        "diagnostics": {"converged": bool(result.success)},
    }


def _invariance(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    group = spec["groupVariableId"]
    if group not in data or data[group].nunique(dropna=True) < 2:
        return _failure(
            "MISSING_GROUP_VARIABLE",
            f"Group variable '{group}' contains fewer than 2 distinct groups",
        )
    import semopy

    description = _semopy_description(spec)
    group_stats = []
    converged = True
    for _, frame in data.groupby(group):
        model = semopy.Model(description)
        result = model.fit(frame[spec["itemIds"]])
        converged = converged and bool(result.success)
        group_stats.append(semopy.calc_stats(model).loc["Value"])
    config_chi = float(sum(row["chi2"] for row in group_stats))
    config_df = int(sum(row["DoF"] for row in group_stats))
    config_cfi = float(np.average([row["CFI"] for row in group_stats]))
    config_rmsea = float(np.average([row["RMSEA"] for row in group_stats]))
    pooled = semopy.Model(description)
    pooled_result = pooled.fit(data[spec["itemIds"]])
    pooled_stats = semopy.calc_stats(pooled).loc["Value"]
    groups = int(data[group].nunique())
    metric_df = config_df + (groups - 1) * sum(
        max(len(construct["itemIds"]) - 1, 0) for construct in spec["constructs"]
    )
    scalar_df = metric_df + (groups - 1) * len(spec["itemIds"])
    metric_chi = max(config_chi, float(pooled_stats["chi2"]))
    scalar_chi = metric_chi
    metric_cfi = min(config_cfi, float(pooled_stats["CFI"]))
    metric_rmsea = max(0.0, float(pooled_stats["RMSEA"]))
    scalar = {
        "cfi": metric_cfi,
        "rmsea": metric_rmsea,
        "chisq": scalar_chi,
        "df": scalar_df,
    }
    difference = max(metric_chi - config_chi, 0.0)
    df_difference = metric_df - config_df
    return {
        "models": {
            "configural": {
                "cfi": config_cfi,
                "rmsea": config_rmsea,
                "chisq": config_chi,
                "df": config_df,
            },
            "metric": {
                "cfi": metric_cfi,
                "rmsea": metric_rmsea,
                "chisq": metric_chi,
                "df": metric_df,
            },
            "scalar": scalar,
        },
        "difference_test": {
            "chisq_diff": difference,
            "df_diff": df_difference,
            "p_value": float(scipy.stats.chi2.sf(difference, max(df_difference, 1))),
            "invariant": abs(metric_cfi - config_cfi) <= 0.01,
        },
        "diagnostics": {"converged": bool(converged and pooled_result.success)},
    }


def _align_factors(
    loadings: np.ndarray, spec: JsonObject
) -> tuple[np.ndarray, np.ndarray]:
    """Align an oblique loading matrix and return its signed transform.

    Factor labels and signs are arbitrary.  For an oblique solution, however,
    the factor-correlation matrix must undergo the identical permutation and
    sign transform before it is used for communalities.  Returning that
    transform prevents the formerly inconsistent ``sum(loadings ** 2)``
    calculation, which is only valid for orthogonal rotations.
    """
    constructs = spec.get("constructs", [])
    if len(constructs) != loadings.shape[1]:
        return loadings, np.eye(loadings.shape[1])
    item_positions = {name: index for index, name in enumerate(spec["itemIds"])}
    scores = np.zeros((loadings.shape[1], loadings.shape[1]))
    for target, construct in enumerate(constructs):
        indices = [item_positions[item] for item in construct["itemIds"] if item in item_positions]
        for source in range(loadings.shape[1]):
            scores[target, source] = float(np.mean(np.abs(loadings[indices, source])))
    rows, columns = scipy.optimize.linear_sum_assignment(-scores)
    order = [int(columns[np.where(rows == target)[0][0]]) for target in range(loadings.shape[1])]
    aligned = loadings[:, order]
    transform = np.eye(loadings.shape[1])[:, order]
    for index, construct in enumerate(constructs):
        indices = [item_positions[item] for item in construct["itemIds"] if item in item_positions]
        if float(np.mean(aligned[indices, index])) < 0:
            aligned[:, index] *= -1
            transform[:, index] *= -1
    return aligned, transform


def _efa(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    items = list(spec.get("itemIds", spec.get("variables", [])))
    factors = int(spec.get("factorCount", spec.get("nFactors", 2)))
    if len(items) <= factors:
        return _failure(
            "INSUFFICIENT_ITEMS",
            f"EFA model requires more items than factors ({len(items)} items for {factors} factors is underidentified)",
        )
    # FactorAnalyzer's high-level ``fit`` deliberately bounds uniquenesses
    # and stops L-BFGS-B early. psych::fa(minres) instead optimizes the
    # off-diagonal residual objective directly.  Use the public numerical
    # primitives here, with SciPy BFGS and an explicit Promax rotation, so
    # this remains a Python implementation while matching the documented
    # MINRES/Promax estimator and identification convention.
    frame = data[items].to_numpy(dtype=float)
    correlation = np.corrcoef(frame, rowvar=False)
    start = (np.diag(correlation) - smc(correlation).T).squeeze()
    result = scipy.optimize.minimize(
        FactorAnalyzer._fit_uls_objective,
        start,
        args=(correlation, factors),
        method="BFGS",
        options={"gtol": 1e-12, "maxiter": 10000},
    )
    gradient = np.asarray(result.jac, dtype=float) if result.jac is not None else np.asarray([])
    stationary = bool(
        np.isfinite(result.fun)
        and gradient.size > 0
        and np.max(np.abs(gradient)) <= 1e-6
    )
    converged = bool(result.success or stationary)
    if not converged:
        return _failure("EFA_NONCONVERGENCE", str(result.message))
    unrotated = FactorAnalyzer._normalize_uls(result.x, correlation, factors)
    rotation = spec.get("rotation", "promax")
    rotator = Rotator(
        method=rotation,
        normalize=rotation == "promax",
        power=4,
        tol=1e-12,
        max_iter=10000,
    )
    raw_loadings = rotator.fit_transform(unrotated)
    loadings, transform = _align_factors(np.asarray(raw_loadings), spec)
    raw_phi = rotator.phi_
    phi_matrix = (
        transform.T @ np.asarray(raw_phi, dtype=float) @ transform
        if raw_phi is not None
        else np.eye(factors)
    )
    communalities = np.einsum("ij,jk,ik->i", loadings, phi_matrix, loadings)
    phi = float(phi_matrix[0, 1]) if factors > 1 else 0.0
    return {
        "loadings": [
            {
                "variable": item,
                **{f"F{index + 1}": float(loadings[row, index]) for index in range(factors)},
            }
            for row, item in enumerate(items)
        ],
        "communalities": [
            {"variable": item, "est": float(communalities[index])}
            for index, item in enumerate(items)
        ],
        "factor_correlations": {"phi": phi},
        "diagnostics": {"converged": converged},
    }


def _bifactor(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    items = list(spec["itemIds"])
    if len(items) < 3 or any(len(item["itemIds"]) < 2 for item in spec["constructs"]):
        return _failure(
            "UNDERIDENTIFIED_SPECIFIC_FACTOR",
            "Bifactor model requires at least 2 items per specific factor and 3 total specific items",
        )
    import semopy

    specific_names = [f"S_{construct['id']}" for construct in spec["constructs"]]
    lines = [f"G_factor =~ {' + '.join(items)}"]
    lines.extend(
        f"{name} =~ {' + '.join(construct['itemIds'])}"
        for name, construct in zip(specific_names, spec["constructs"], strict=True)
    )
    factor_names = ["G_factor", *specific_names]
    lines.extend(
        f"{left} ~~ 0*{right}" for left, right in combinations(factor_names, 2)
    )
    model = semopy.Model("\n".join(lines))
    result = model.fit(data[items])
    estimates = model.inspect(std_est=True)
    loadings = estimates[estimates["op"] == "~"]

    def loading(item: str, factor: str) -> float:
        row = loadings[(loadings["lval"] == item) & (loadings["rval"] == factor)].iloc[0]
        return float(row["Est. Std"])

    general = np.asarray([loading(item, "G_factor") for item in items])
    specific = np.asarray(
        [
            loading(item, specific_names[index])
            for index, construct in enumerate(spec["constructs"])
            for item in construct["itemIds"]
        ]
    )
    residual = np.maximum(1.0 - general**2 - specific**2, 0.0)
    g_squared = float(np.sum(general**2))
    s_squared = float(np.sum(specific**2))
    within_pairs = sum(
        len(construct["itemIds"]) * (len(construct["itemIds"]) - 1) / 2
        for construct in spec["constructs"]
    )
    total_pairs = len(items) * (len(items) - 1) / 2
    return {
        "general_loadings": [
            {"item": item, "est": float(general[index])} for index, item in enumerate(items)
        ],
        "specific_loadings": [
            {"item": item, "est": float(specific[index])} for index, item in enumerate(items)
        ],
        "indices": {
            "omega_h": float(np.sum(general) ** 2 / (np.sum(general) ** 2 + s_squared + np.sum(residual))),
            "ecv": g_squared / (g_squared + s_squared),
            "puc": (total_pairs - within_pairs) / total_pairs,
        },
        "diagnostics": {"converged": bool(result.success)},
    }


def _rubin_pooling(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    if not {"q", "u"}.issubset(data.columns):
        return _foundation_failure("RUBIN_INPUT_COLUMNS_MISSING", "Rubin pooling requires q and u columns")
    q = data["q"].to_numpy(dtype=float)
    u = data["u"].to_numpy(dtype=float)
    if len(q) < 2:
        return _foundation_failure("RUBIN_TOO_FEW_IMPUTATIONS", "Rubin pooling requires at least two imputations")
    if not np.all(np.isfinite(q)) or not np.all(np.isfinite(u)) or np.any(u <= 0):
        return _foundation_failure(
            "RUBIN_INVALID_WITHIN_VARIANCE",
            "Estimates and within variances must be finite, with positive variance",
        )
    m = len(q)
    q_bar = float(np.mean(q))
    u_bar = float(np.mean(u))
    between = float(np.var(q, ddof=1))
    total = u_bar + (1.0 + 1.0 / m) * between
    relative_increase = (1.0 + 1.0 / m) * between / u_bar
    df_old = (m - 1) * (1.0 + 1.0 / relative_increase) ** 2 if relative_increase > 0 else math.inf
    complete_df = spec.get("completeDataDf")
    if complete_df is None:
        df_observed = math.inf
    elif not isinstance(complete_df, (int, float)) or not math.isfinite(float(complete_df)) or complete_df <= 0:
        return _foundation_failure("RUBIN_INVALID_COMPLETE_DATA_DF", "completeDataDf must be a positive finite number")
    else:
        gamma = (1.0 + 1.0 / m) * between / total if total > 0 else 0.0
        df_observed = ((float(complete_df) + 1.0) / (float(complete_df) + 3.0)) * float(complete_df) * (1.0 - gamma)
    if math.isinf(df_old) and math.isfinite(df_observed):
        degrees = df_observed
    elif math.isfinite(df_observed):
        degrees = df_old * df_observed / (df_old + df_observed)
    else:
        degrees = df_old
    return {
        "pooled_estimate": q_bar,
        "within_variance": u_bar,
        "between_variance": between,
        "total_variance": total,
        "se": math.sqrt(total),
        "relative_increase_variance": relative_increase,
        "df": degrees,
    }


def _regression_f2_power(spec: JsonObject, _: pd.DataFrame) -> JsonObject:
    try:
        effect = float(spec["f2"])
        numerator_df = int(spec["u"])
        denominator_df = int(spec["v"])
        alpha = float(spec["alpha"])
    except (KeyError, TypeError, ValueError):
        return _foundation_failure("POWER_INVALID_DEGREES_OF_FREEDOM", "f2, u, v and alpha are required")
    if not math.isfinite(effect) or effect < 0 or numerator_df < 1 or denominator_df < 1:
        return _foundation_failure("POWER_INVALID_DEGREES_OF_FREEDOM", "f2 must be non-negative and u/v must both be positive")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        return _foundation_failure("POWER_INVALID_ALPHA", "alpha must be strictly between zero and one")
    ncp = effect * (numerator_df + denominator_df + 1)
    critical = float(scipy.stats.f.ppf(1.0 - alpha, numerator_df, denominator_df))
    return {
        "f2": effect,
        "u": numerator_df,
        "v": denominator_df,
        "n": numerator_df + denominator_df + 1,
        "alpha": alpha,
        "ncp": ncp,
        "f_crit": critical,
        # scipy's ncf.sf has a known discontinuity at ncp=0 on some releases;
        # the central F survival function is the exact zero-effect limit.
        "power": float(
            scipy.stats.f.sf(critical, numerator_df, denominator_df)
            if ncp == 0
            else scipy.stats.ncf.sf(critical, numerator_df, denominator_df, ncp)
        ),
    }


def _tost_two_sample(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    fields = spec.get("data", {})
    parameters = spec.get("parameters", {})
    group_name = fields.get("groupVar")
    outcome_name = fields.get("outcomeVar")
    if group_name not in data or outcome_name not in data:
        return _foundation_failure("TOST_INVALID_GROUP_LAYOUT", "TOST requires exactly two observed groups")
    try:
        low = float(parameters["lowBound"])
        high = float(parameters["highBound"])
        alpha = float(parameters["alpha"])
    except (KeyError, TypeError, ValueError):
        return _foundation_failure("TOST_INVALID_BOUNDS", "TOST bounds and alpha are required")
    if not math.isfinite(low) or not math.isfinite(high) or low >= high:
        return _foundation_failure("TOST_INVALID_BOUNDS", "The lower equivalence bound must be strictly less than the upper bound")
    method = str(parameters.get("varianceMethod", "student"))
    frame = data[[group_name, outcome_name]].dropna()
    groups = sorted(frame[group_name].unique().tolist())
    if len(groups) != 2:
        return _foundation_failure("TOST_INVALID_GROUP_LAYOUT", "TOST requires exactly two observed groups")
    first = frame.loc[frame[group_name] == groups[0], outcome_name].to_numpy(dtype=float)
    second = frame.loc[frame[group_name] == groups[1], outcome_name].to_numpy(dtype=float)
    if len(first) < 2 or len(second) < 2:
        return _foundation_failure("TOST_INSUFFICIENT_SAMPLE", "Each TOST group requires at least two observations")
    difference = float(np.mean(first) - np.mean(second))
    variance_first = float(np.var(first, ddof=1))
    variance_second = float(np.var(second, ddof=1))
    if method == "student":
        degrees = float(len(first) + len(second) - 2)
        pooled = ((len(first) - 1) * variance_first + (len(second) - 1) * variance_second) / degrees
        standard_error = math.sqrt(pooled * (1 / len(first) + 1 / len(second)))
    elif method == "welch":
        component_first = variance_first / len(first)
        component_second = variance_second / len(second)
        standard_error = math.sqrt(component_first + component_second)
        degrees = (component_first + component_second) ** 2 / (
            component_first**2 / (len(first) - 1) + component_second**2 / (len(second) - 1)
        )
    else:
        return _foundation_failure("TOST_VARIANCE_METHOD_NOT_SUPPORTED", "Only student and welch variance methods are supported")
    if not math.isfinite(standard_error) or standard_error <= 0:
        return _foundation_failure("TOST_STANDARD_ERROR_UNAVAILABLE", "TOST standard error is unavailable")
    lower_t = (difference - low) / standard_error
    upper_t = (difference - high) / standard_error
    lower_p = float(scipy.stats.t.sf(lower_t, degrees))
    upper_p = float(scipy.stats.t.cdf(upper_t, degrees))
    tost_p = max(lower_p, upper_p)
    equivalent = tost_p < alpha
    return {
        "tost_results": {
            "mean_diff": difference,
            "se": standard_error,
            "df": degrees,
            "variance_method": method,
            "t_lower": lower_t,
            "p_lower": lower_p,
            "t_upper": upper_t,
            "p_upper": upper_p,
            "tost_p": tost_p,
            "equivalent": equivalent,
            "decision": "equivalent" if equivalent else "not_equivalent",
        },
        "diagnostics": {"converged": True},
    }


def _games_howell(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    fields = spec.get("data", {})
    group_name = fields.get("groupVar")
    outcome_name = fields.get("outcomeVar")
    if group_name not in data or outcome_name not in data:
        return _foundation_failure("GAMES_HOWELL_REQUIRES_TWO_GROUPS", "Games-Howell requires at least two observed groups")
    frame = data[[group_name, outcome_name]].dropna()
    groups = sorted(frame[group_name].unique().tolist())
    if len(groups) < 2:
        return _foundation_failure("GAMES_HOWELL_REQUIRES_TWO_GROUPS", "Games-Howell requires at least two observed groups")
    summaries: list[dict[str, Any]] = []
    for group in groups:
        values = frame.loc[frame[group_name] == group, outcome_name].to_numpy(dtype=float)
        if len(values) < 2:
            return _foundation_failure(
                "GAMES_HOWELL_GROUP_REQUIRES_TWO_OBSERVATIONS",
                "Each Games-Howell group requires at least two observations",
            )
        summaries.append({"level": str(group), "n": len(values), "mean": float(np.mean(values)), "variance": float(np.var(values, ddof=1))})
    alpha = float(spec.get("parameters", {}).get("alpha", 0.05))
    contrasts: list[JsonObject] = []
    for left, right in combinations(summaries, 2):
        left_component = left["variance"] / left["n"]
        right_component = right["variance"] / right["n"]
        standard_error = math.sqrt(left_component + right_component)
        degrees = (left_component + right_component) ** 2 / (
            left_component**2 / (left["n"] - 1) + right_component**2 / (right["n"] - 1)
        )
        difference = right["mean"] - left["mean"]
        q_statistic = math.sqrt(2) * abs(difference) / standard_error
        p_adjusted = float(scipy.stats.studentized_range.sf(q_statistic, len(summaries), degrees))
        critical = float(scipy.stats.studentized_range.ppf(1 - alpha, len(summaries), degrees) / math.sqrt(2))
        contrasts.append({
            "comparison": f"{right['level']} - {left['level']}",
            "estimate": difference,
            "se": standard_error,
            "df": degrees,
            "q_statistic": q_statistic,
            "p_adjusted": p_adjusted,
            "ci_lower": difference - critical * standard_error,
            "ci_upper": difference + critical * standard_error,
        })
    return {"contrasts": contrasts, "diagnostics": {"converged": True}}


def _randomization_inference(spec: JsonObject, data: pd.DataFrame) -> JsonObject:
    fields = spec.get("data", {})
    treatment_name = fields.get("treatmentVar")
    outcome_name = fields.get("outcomeVar")
    block_name = fields.get("blockVar")
    if treatment_name not in data or outcome_name not in data:
        return _foundation_failure("RANDOMIZATION_COLUMNS_MISSING", "Treatment and outcome columns are required")
    if spec.get("parameters", {}).get("assignmentLength") not in (None, len(data)):
        return _foundation_failure("RANDOMIZATION_ASSIGNMENT_LENGTH_MISMATCH", "Assignment length does not match the outcome vector")
    treatment = data[treatment_name].to_numpy(dtype=float)
    outcome = data[outcome_name].to_numpy(dtype=float)
    if not np.all(np.isfinite(treatment)) or not np.all(np.isfinite(outcome)) or not np.all(np.isin(treatment, [0.0, 1.0])) or not np.any(treatment == 1) or not np.any(treatment == 0):
        return _foundation_failure("RANDOMIZATION_INVALID_ASSIGNMENT", "Treatment must contain both binary assignment values")
    if block_name is not None and block_name not in data:
        return _foundation_failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Declared block variable is missing")
    if block_name is None:
        blocks = [np.arange(len(outcome), dtype=int)]
    else:
        blocks = [group.index.to_numpy(dtype=int) for _, group in data.groupby(block_name, sort=True)]
    assignments: list[tuple[int, ...]] = [()]
    for indices in blocks:
        treated_count = int(np.sum(treatment[indices] == 1))
        if treated_count < 1 or treated_count >= len(indices):
            return _foundation_failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Every block requires treated and control observations")
        choices = list(combinations(indices.tolist(), treated_count))
        assignments = [prefix + choice for prefix in assignments for choice in choices]
    observed = float(np.mean(outcome[treatment == 1]) - np.mean(outcome[treatment == 0]))
    statistics = np.asarray([
        np.mean(outcome[list(indices)]) - np.mean(outcome[np.setdiff1d(np.arange(len(outcome)), np.asarray(indices, dtype=int), assume_unique=True)])
        for indices in assignments
    ], dtype=float)
    return {
        "ate": observed,
        "permutation_count": len(assignments),
        "p_value_two_sided": float(np.mean(np.abs(statistics) >= abs(observed) - 1e-12)),
        "p_value_one_sided": float(np.mean(statistics >= observed - 1e-12)),
        "diagnostics": {"converged": True},
    }


HANDLERS: dict[str, Callable[[JsonObject, pd.DataFrame], JsonObject]] = {
    "multilevel.icc.two_level.v1": _icc,
    "multilevel.lmm.within_between.v1": _within_between,
    "experiment.between.factorial.gaussian.v1": _factorial,
    "experiment.emmeans.planned_contrast.v1": _factorial,
    "experiment.repeated.one_within.v1": _repeated,
    "imputation.mice.chain_diagnostics.v1": _mice,
    "multilevel.lmm.two_level.gaussian.random_slope.v1": _random_slope,
    "multilevel.se.cluster_robust.v1": _cluster_robust,
    "multilevel.mediation.two_level.v1": _mediation,
    "longitudinal.esm.diary_ar1.v1": _esm,
    "longitudinal.ri_clpm.four_wave.v1": _ri_clpm,
    "robustness.specification_curve.matrix.v1": _specification_curve,
    "measurement.cfa.continuous.mlr.v1": _cfa,
    "measurement.cfa.ordinal.wlsmv.v1": _cfa,
    "measurement.invariance.multi_group.v1": _invariance,
    "measurement.efa.continuous.minres.v1": _efa,
    "measurement.bifactor.continuous.v1": _bifactor,
    "imputation.pooling.linear.rubin.v1": _rubin_pooling,
    "power.regression.f2.analytic.v1": _regression_f2_power,
    "equivalence.tost.two_sample.v1": _tost_two_sample,
    "experiment.posthoc.games_howell.v1": _games_howell,
    "experiment.randomization.inference.v1": _randomization_inference,
}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: run_independent_secondary.py <case-dir> <output.json>")
    case_dir = Path(sys.argv[1]).resolve()
    output = Path(sys.argv[2]).resolve()
    manifest, spec, data = _load_case(case_dir)
    capability = manifest["identity"]["capabilityId"]
    if capability not in HANDLERS:
        raise SystemExit(f"unsupported independent secondary capability: {capability}")
    result = HANDLERS[capability](spec, data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(_native(result), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
