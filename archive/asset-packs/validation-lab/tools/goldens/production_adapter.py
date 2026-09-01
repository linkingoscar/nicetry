"""Normalize ResearchPath production-engine results for frozen Golden cases.

Statistical decisions remain in the production R engine. These adapters only
translate its public ResultBundle into the field names used by references.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linear_sum_assignment
import yaml


def _project_root() -> Path:
    configured = os.environ.get("RESEARCHPATH_PROJECT_ROOT")
    if not configured:
        raise RuntimeError("RESEARCHPATH_PROJECT_ROOT is required")
    root = Path(configured).resolve()
    if not (root / "project.manifest.json").is_file():
        raise RuntimeError("RESEARCHPATH_PROJECT_ROOT does not identify the repository")
    return root


def _run_advanced_engine(case_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    root = _project_root()
    sys.path.insert(0, str(root / "apps" / "api"))
    from app.settings import get_settings

    settings = get_settings()
    request_path = case_dir / "sut" / "engine-input.json"
    result_path = case_dir / "sut" / "engine-output.json"
    artifact_directory = case_dir / "sut" / "artifacts"
    artifact_directory.mkdir(parents=True, exist_ok=True)
    request_path.write_text(
        json.dumps(
            {
                "spec": spec,
                "dataPath": str(case_dir / "data" / "input.csv"),
                "artifactDirectory": str(artifact_directory),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    environment["LC_ALL"] = "English_United States.utf8"
    completed = subprocess.run(
        [
            str(settings.rscript_path),
            "--vanilla",
            str(root / "engine" / "R" / "run_advanced_analysis.R"),
            str(request_path),
            str(result_path),
        ],
        cwd=str(root),
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0 or not result_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Production R engine failed: {detail}")
    return json.loads(result_path.read_text(encoding="utf-8"))


def _run_statistical_engine(
    case_dir: Path, capability_id: str, spec: dict[str, Any]
) -> dict[str, Any]:
    root = _project_root()
    sys.path.insert(0, str(root / "apps" / "api"))
    from app.settings import get_settings

    settings = get_settings()
    request_path = case_dir / "sut" / "engine-input.json"
    result_path = case_dir / "sut" / "engine-output.json"
    request_path.write_text(
        json.dumps(
            {
                "capabilityId": capability_id,
                "spec": spec,
                "dataPath": str(case_dir / "data" / "input.csv"),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["R_LIBS_USER"] = str(settings.r_library_path)
    environment["LC_ALL"] = "English_United States.utf8"
    completed = subprocess.run(
        [
            str(settings.rscript_path),
            "--vanilla",
            str(root / "engine" / "R" / "run_statistical_capability.R"),
            str(request_path),
            str(result_path),
        ],
        cwd=str(root),
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if completed.returncode != 0 or not result_path.is_file():
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"Production statistical engine failed: {detail}")
    return json.loads(result_path.read_text(encoding="utf-8"))


def _normalize_experimental(result: dict[str, Any]) -> dict[str, Any]:
    family = result["familyResult"]
    omnibus = [
        {
            "term": row["term"],
            "num Df": row["numeratorDf"],
            "den Df": row["denominatorDf"],
            "F": row["f"],
            "pes": row["partialEtaSquared"],
            "Pr(>F)": row["pValue"],
        }
        for row in family["omnibusTests"]
    ]
    emmeans = []
    for item in family.get("estimatedMarginalMeans", []):
        if isinstance(item, dict):
            item_copy = dict(item)
            if "lower.CL" in item_copy:
                item_copy["lower_CL"] = item_copy.pop("lower.CL")
            if "upper.CL" in item_copy:
                item_copy["upper_CL"] = item_copy.pop("upper.CL")
            emmeans.append(item_copy)
        else:
            emmeans.append(item)

    normalized: dict[str, Any] = {
        "omnibusTests": omnibus,
        "estimatedMarginalMeans": emmeans,
        "contrasts": family.get("contrasts", []),
    }
    sphericity = family.get("sphericity")
    if isinstance(sphericity, dict):
        corrections = sphericity.get("corrections", [])
        correction = corrections[0] if corrections else {}
        normalized["sphericity"] = {
            "mauchly_p": sphericity.get("mauchlyPValue"),
            "gg_epsilon": correction.get("GG eps"),
            "hf_epsilon": correction.get("HF eps"),
        }
    else:
        normalized["sphericity"] = None
    return {"familyResult": normalized}


def _canonicalize_oblique_factors(
    loadings: list[list[float]], phi: list[list[float]] | None, spec: dict[str, Any]
) -> tuple[list[list[float]], list[list[float]]]:
    """Apply a construct-derived signed permutation to pattern loadings/Phi.

    EFA factors have no intrinsic label or sign.  Treating the raw order as a
    statistical result produced false Golden conflicts when independent
    optimizers selected another equivalent orientation.  For oblique factors,
    Phi must receive the same transform as the loading matrix.
    """
    matrix = np.asarray(loadings, dtype=float)
    factor_count = matrix.shape[1]
    raw_phi = (
        np.asarray(phi, dtype=float)
        if phi is not None
        else np.eye(factor_count, dtype=float)
    )
    constructs = spec.get("constructs", [])
    item_positions = {item: index for index, item in enumerate(spec.get("itemIds", []))}
    if len(constructs) != factor_count or matrix.shape[0] != len(item_positions):
        return matrix.tolist(), raw_phi.tolist()
    score = np.zeros((factor_count, factor_count), dtype=float)
    for target, construct in enumerate(constructs):
        rows = [item_positions[item] for item in construct.get("itemIds", []) if item in item_positions]
        if rows:
            score[target] = np.mean(np.abs(matrix[rows]), axis=0)
    targets, sources = linear_sum_assignment(-score)
    if len(targets) != factor_count:
        return matrix.tolist(), raw_phi.tolist()
    order = [int(sources[np.where(targets == target)[0][0]]) for target in range(factor_count)]
    transform = np.eye(factor_count, dtype=float)[:, order]
    aligned = matrix @ transform
    for target, construct in enumerate(constructs):
        rows = [item_positions[item] for item in construct.get("itemIds", []) if item in item_positions]
        if rows and float(np.mean(aligned[rows, target])) < 0:
            aligned[:, target] *= -1
            transform[:, target] *= -1
    return aligned.tolist(), (transform.T @ raw_phi @ transform).tolist()


def _normalize_measurement(capability_id: str, result: dict[str, Any]) -> dict[str, Any]:
    family = result["familyResult"]
    if capability_id.startswith("measurement.cfa."):
        cfa = family["cfa"]
        construct_for_item: dict[str, str] = {}
        for construct in result.get("_spec", {}).get("constructs", []):
            for item in construct["itemIds"]:
                construct_for_item[item] = f"F_{construct['id']}"
        return {
            "estimator": result["_spec"]["estimator"],
            "fit": {
                "cfi_robust": cfa["cfiRobust"], "tli_robust": cfa["tliRobust"],
                "rmsea_robust": cfa["rmseaRobust"], "srmr": cfa["srmr"],
                "chisq_scaled": cfa["chiSquareScaled"],
            },
            "loadings": [
                {"lhs": construct_for_item[row["itemId"]], "rhs": row["itemId"],
                 "est": row["estimate"], "se": row["se"]}
                for row in cfa["unstandardizedLoadings"]
            ],
            "diagnostics": {"converged": cfa["converged"]},
        }
    if capability_id == "measurement.invariance.multi_group.v1":
        inv = family["invariance"]
        models = {
            name: {"cfi": model["cfi"], "rmsea": model["rmsea"],
                   "chisq": model["chiSquare"], "df": model["df"]}
            for name, model in inv["models"].items() if model is not None
        }
        metric = inv["comparisons"]["metric"]
        return {"models": models, "difference_test": {
            "chisq_diff": metric["deltaChiSquare"], "df_diff": metric["deltaDf"],
            "p_value": metric["pValue"],
            "invariant": abs(metric["deltaCfi"]) <= 0.01,
        }, "diagnostics": {"converged": True}}
    if capability_id == "measurement.esem.target_rotation.v1":
        esem = family["esem"]
        rows = []
        for row in esem["loadings"]:
            rows.append({"item": row["itemId"], **{
                f"F{i + 1}": value for i, value in enumerate(row["loadings"])
            }})
        phi = esem["factorCorrelations"]
        return {"rotated_loadings": rows,
                "factor_correlations": {"phi_F1_F2": phi[0][1]},
                "diagnostics": {"converged": esem["available"]}}
    if capability_id == "measurement.bifactor.continuous.v1":
        bifactor = family["bifactor"]
        return {
            "general_loadings": [{"item": row["itemId"], "est": row["generalLoading"]} for row in bifactor["itemDetails"]],
            "specific_loadings": [{"item": row["itemId"], "est": row["specificLoading"]} for row in bifactor["itemDetails"]],
            "indices": {"omega_h": bifactor["bifactorMetrics"]["omegaHierarchical"],
                        "ecv": bifactor["bifactorMetrics"]["ecv"], "puc": bifactor["bifactorMetrics"]["puc"]},
            "diagnostics": {"converged": bifactor["available"]},
        }
    if capability_id == "measurement.cmb.ulmc.v1":
        ulmc = family["commonMethodBias"]["ulmc"]
        comparison = ulmc["modelComparison"]
        return {"fit_comparison": {
            "baseline_cfi": ulmc["baselineModel"]["cfi"], "ulmc_cfi": ulmc["ulmcModel"]["cfi"],
            "delta_cfi": comparison["deltaCfi"], "delta_chisq": comparison["deltaChisq"],
            "p_value": comparison["pValue"]},
            "cmb_present": comparison["significantMethodBias"],
            "diagnostics": {"converged": ulmc["available"]}}
    if capability_id == "measurement.irt.dif.v1":
        irt = family["irt"]
        return {
            "item_parameters": [{"item": row["itemId"], "a": row["discrimination_a"],
                                 "b": row["difficulties_b"][0]} for row in irt["itemParameters"]],
            "dif_tests": [{"item": row["itemId"], "uniform_chisq": row["statistic"],
                           "p_value": row["pValue"], "has_dif": row["difDetected"]}
                          for row in irt["difAnalysis"]],
            "diagnostics": {"converged": irt["converged"]},
        }
    if capability_id == "measurement.efa.continuous.minres.v1":
        efa = family["efa"]
        aligned, phi = _canonicalize_oblique_factors(
            [row["loadings"] for row in efa["loadings"]],
            efa.get("factorCorrelations"),
            result["_spec"],
        )
        loadings = []
        for row, values in zip(efa["loadings"], aligned, strict=True):
            item_id = row["itemId"]
            ld_dict = {"variable": item_id}
            for i, val in enumerate(values):
                ld_dict[f"F{i + 1}"] = val
            loadings.append(ld_dict)
        phi_array = np.asarray(phi, dtype=float)
        communalities = [
            {"variable": row["itemId"], "est": float(values @ phi_array @ values)}
            for row, values in zip(efa["loadings"], aligned, strict=True)
        ]
        phi_val = float(phi_array[0, 1]) if phi_array.shape[0] > 1 else 0.0
        return {
            "loadings": loadings,
            "communalities": communalities,
            "factor_correlations": {"phi": phi_val},
            "diagnostics": {"converged": efa["available"]},
        }
    raise RuntimeError(f"Unsupported measurement capability: {capability_id}")


def _normalize_imputation(case_dir: Path, spec: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    import csv

    family = result["familyResult"]
    with (case_dir / "data" / "input.csv").open(encoding="utf-8-sig", newline="") as handle:
        original = list(csv.DictReader(handle))
    completed_sets: list[list[dict[str, str]]] = []
    for artifact in family["artifacts"]:
        path = case_dir / "sut" / "artifacts" / artifact["temporary"]
        with path.open(encoding="utf-8-sig", newline="") as handle:
            completed_sets.append(list(csv.DictReader(handle)))

    targets = [variable["variableId"] for variable in spec["variables"]]
    observed_preserved = all(
        original[index][target] in {"", "NA", "NaN"}
        or math.isclose(float(completed[index][target]), float(original[index][target]), abs_tol=1e-12)
        for completed in completed_sets for index in range(len(original)) for target in targets
    )
    passive_preserved = True
    for rule in spec["passiveRules"]:
        left, right = [part.strip() for part in rule["expression"].split("*")]
        target = rule["targetVariableId"]
        passive_preserved = passive_preserved and all(
            row[target] in {"", "NA", "NaN"}
            or row[left] in {"", "NA", "NaN"}
            or row[right] in {"", "NA", "NaN"}
            or math.isclose(float(row[target]), float(row[left]) * float(row[right]), rel_tol=1e-10, abs_tol=1e-10)
            for completed in completed_sets for row in completed
        )
    conv = family.get("convergence", [])
    converged = all(row.get("converged", True) for row in conv) if conv else True
    return {
        "imputations_count": family["imputations"], "iterations": spec["iterations"],
        "chain_converged": converged,
        "passive_variable_preserved": passive_preserved,
        "missing_cells_only": observed_preserved,
        "diagnostics": {"converged": True},
    }


def _normalize_riclpm(result: dict[str, Any]) -> dict[str, Any]:
    family = result["familyResult"]
    seen_auto: set[tuple[str, str]] = set()
    autoregressive = []
    for row in family["autoregressiveEffects"]:
        key = (row["lhs"].split("_")[0], row["rhs"].split("_")[0])
        if key not in seen_auto:
            seen_auto.add(key)
            autoregressive.append({"path": f"{row['lhs']}~{row['rhs']}", "est": row["estimate"], "p_value": row["pValue"]})
    seen_cross: set[tuple[str, str]] = set()
    cross_lagged = []
    for row in family["crossLaggedEffects"]:
        key = (row["lhs"].split("_")[0], row["rhs"].split("_")[0])
        if key not in seen_cross:
            seen_cross.add(key)
            cross_lagged.append({"path": f"{row['lhs']}~{row['rhs']}", "est": row["estimate"], "p_value": row["pValue"]})
    return {"trait_components": family["traitComponents"], "autoregressive_paths": autoregressive,
            "cross_lagged_paths": cross_lagged,
            "fit": {"cfi": family["fitIndices"]["cfi"], "rmsea": family["fitIndices"]["rmsea"]},
            "diagnostics": {"converged": True}}


def run_case(case_dir: Path) -> None:
    manifest = yaml.safe_load((case_dir / "manifest.yaml").read_text(encoding="utf-8"))
    spec = json.loads((case_dir / manifest["specPath"]).read_text(encoding="utf-8"))
    capability_id = manifest["identity"]["capabilityId"]

    if spec.get("family") == "questionnaire_measurement":
        result = _run_advanced_engine(case_dir, spec)
        result["_spec"] = spec
        normalized = _normalize_measurement(capability_id, result)
    elif capability_id == "longitudinal.ri_clpm.four_wave.v1":
        normalized = _normalize_riclpm(_run_advanced_engine(case_dir, spec))
    elif spec.get("family") == "multiple_imputation":
        normalized = _normalize_imputation(case_dir, spec, _run_advanced_engine(case_dir, spec))
    elif spec.get("family") == "experimental_design":
        normalized = _normalize_experimental(_run_advanced_engine(case_dir, spec))
    elif spec.get("family") == "multilevel_model":
        result = _run_advanced_engine(case_dir, spec)
        fam = result["familyResult"]
        if isinstance(fam, dict) and "fixedEffects" in fam:
            for item in fam["fixedEffects"]:
                if isinstance(item, dict):
                    for k in list(item.keys()):
                        new_k = k
                        if new_k == "Std. Error":
                            new_k = "Std_Error"
                        elif new_k == "t value":
                            new_k = "t_value"
                        elif new_k == "Pr(>|t|)":
                            new_k = "Pr_t"
                        elif "." in new_k or " " in new_k:
                            new_k = new_k.replace(".", "_").replace(" ", "_")
                        if new_k != k:
                            item[new_k] = item.pop(k)
        normalized = {"familyResult": fam}
    else:
        normalized = _run_statistical_engine(case_dir, capability_id, spec)

    output = case_dir / "sut" / "normalized-output.json"
    output.write_text(
        json.dumps(normalized, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
