"""Materialize the audited four-case Golden matrices for foundational methods.

This is an explicit Golden-refresh migration, not a CI generator.  It is kept
in version control so the deterministic parameter fixtures, source metadata,
and independent runner bindings can be reviewed and reproduced without
hand-editing dozens of nearly identical assets.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
GOLDENS = ROOT / "tests" / "goldens"
REPO_URL = "https://github.com/linkingoscar/nicetry"

PRIMARY_RUNNER = """import os, runpy
from pathlib import Path

runpy.run_path(
    str(Path(os.environ[\"RESEARCHPATH_PROJECT_ROOT\"]) / \"reference\" / \"generators\" / \"python\" / \"run_statistical_reference.py\"),
    run_name=\"__main__\",
)
"""

SECONDARY_RUNNER = """from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

root = Path(os.environ[\"RESEARCHPATH_PROJECT_ROOT\"]).resolve()
case_dir = Path.cwd()
generator = root / \"reference\" / \"generators\" / \"python\" / \"run_independent_secondary.py\"
output = case_dir / \"reference\" / \"secondary\" / \"normalized-output.json\"
completed = subprocess.run(
    [sys.executable, str(generator), str(case_dir), str(output)],
    cwd=str(case_dir), capture_output=True, text=True, timeout=120,
)
if completed.returncode != 0:
    raise RuntimeError((completed.stderr or completed.stdout).strip())
"""

SUT_RUNNER = """import os
import sys
from pathlib import Path

sys.path.insert(0, os.environ[\"RESEARCHPATH_PROJECT_ROOT\"])
from tools.goldens.production_adapter import run_case

run_case(Path.cwd())
"""

LICENSE = "CC0-1.0 Universal Dedicated to Public Domain\n"


def numeric(path: str, abs_tolerance: float = 1e-8, rel_tolerance: float = 1e-7) -> dict[str, Any]:
    return {
        "path": path,
        "comparator": "absolute_relative",
        "absTolerance": abs_tolerance,
        "relTolerance": rel_tolerance,
    }


def exact(path: str) -> dict[str, Any]:
    return {"path": path, "comparator": "exact"}


FAILURE_RULES = [
    exact("status"),
    exact("failure.reasonCode"),
    exact("failure.message"),
    exact("failure.mustNotReturnEstimates"),
    exact("failure.mustNotFallback"),
]

RUBIN_RULES = [
    numeric(path, 1e-8, 1e-7)
    for path in (
        "pooled_estimate", "within_variance", "between_variance", "total_variance",
        "se", "relative_increase_variance", "df",
    )
]
POWER_RULES = [
    exact(path) for path in ("u", "v", "n")
] + [numeric(path, 1e-8, 1e-7) for path in ("f2", "alpha", "ncp", "f_crit", "power")]
TOST_RULES = [
    numeric(path, 1e-8, 1e-7)
    for path in (
        "tost_results.mean_diff", "tost_results.se", "tost_results.df", "tost_results.t_lower",
        "tost_results.p_lower", "tost_results.t_upper", "tost_results.p_upper", "tost_results.tost_p",
    )
] + [exact("tost_results.variance_method"), exact("tost_results.equivalent"), exact("tost_results.decision"), exact("diagnostics.converged")]
RANDOMIZATION_RULES = [
    numeric(path, 1e-8, 1e-7)
    for path in ("ate", "p_value_two_sided", "p_value_one_sided")
] + [exact("permutation_count"), exact("diagnostics.converged")]
GAMES_RULES = [
    numeric(path, 1e-6, 1e-5)
    for index in range(3)
    for path in (
        f"contrasts[{index}].estimate", f"contrasts[{index}].se", f"contrasts[{index}].df",
        f"contrasts[{index}].q_statistic", f"contrasts[{index}].p_adjusted",
        f"contrasts[{index}].ci_lower", f"contrasts[{index}].ci_upper",
    )
] + [
    exact(f"contrasts[{index}].comparison") for index in range(3)
] + [exact("diagnostics.converged")]


def csv_text(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join([",".join(headers), *[",".join(str(value) for value in row) for row in rows]]) + "\n"


def case(
    case_id: str,
    scenario: str,
    spec: dict[str, Any],
    data: str,
    rules: list[dict[str, Any]],
    invariants: dict[str, str],
    source_note: str,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "scenario": scenario,
        "spec": spec,
        "data": data,
        "rules": rules,
        "invariants": invariants,
        "source_note": source_note,
    }


MATRICES: dict[str, dict[str, Any]] = {
    "imputation.pooling.linear.rubin.v1": {
        "family": "imputation",
        "primary": "mice_pool_scalar",
        "secondary": "python_rubin_formulas",
        "readme": "R mice::pool.scalar and an independent Python Rubin/Barnard--Rubin implementation.",
        "evidence": ["G2", "G3", "G6", "G7"],
        "cases": [
            case("rubin_standard", "normal_typical", {"method": "rubin_pooling", "completeDataDf": None},
                 csv_text(["imp", "q", "u"], [[1, 1.2, 0.04], [2, 1.4, 0.04], [3, 1.1, 0.04], [4, 1.3, 0.04], [5, 1.5, 0.04]]),
                 RUBIN_RULES, {"within_variance": "non_negative", "between_variance": "non_negative", "total_variance": "non_negative", "se": "non_negative"}, "Five completed-analysis estimates with common within variance."),
            case("rubin_unequal_within", "legal_complex", {"method": "rubin_pooling", "completeDataDf": None},
                 csv_text(["imp", "q", "u"], [[1, 1.2, 0.04], [2, 1.4, 0.09], [3, 1.1, 0.05], [4, 1.5, 0.08], [5, 1.3, 0.06]]),
                 RUBIN_RULES, {"within_variance": "non_negative", "between_variance": "non_negative", "total_variance": "non_negative", "se": "non_negative"}, "Unequal within-imputation variances exercise Rubin total variance."),
            case("rubin_zero_between", "degenerate_boundary", {"method": "rubin_pooling", "completeDataDf": 100},
                 csv_text(["imp", "q", "u"], [[1, 2.0, 0.05], [2, 2.0, 0.05], [3, 2.0, 0.05], [4, 2.0, 0.05], [5, 2.0, 0.05]]),
                 RUBIN_RULES, {"within_variance": "non_negative", "between_variance": "non_negative", "total_variance": "non_negative", "se": "non_negative"}, "Zero between-imputation variance with finite complete-data df."),
            case("rubin_invalid_m", "expected_failure", {"method": "rubin_pooling", "completeDataDf": 100},
                 csv_text(["imp", "q", "u"], [[1, 1.5, 0.04]]), FAILURE_RULES, {}, "One-imputation fixture must be rejected before pooling."),
        ],
    },
    "power.regression.f2.analytic.v1": {
        "family": "power",
        "primary": "r_pwr_f2",
        "secondary": "scipy_noncentral_f",
        "readme": "R pwr::pwr.f2.test and SciPy noncentral-F survival-function reference.",
        "evidence": ["G2", "G3", "G6", "G7"],
        "cases": [
            case("regression_f2_standard", "normal_typical", {"f2": 0.15, "u": 3, "v": 96, "alpha": 0.05},
                 csv_text(["fixture"], [["standard"]]), POWER_RULES, {"power": "probability"}, "Deterministic analytic f-squared fixture."),
            case("regression_f2_high_u", "legal_complex", {"f2": 0.25, "u": 8, "v": 120, "alpha": 0.01},
                 csv_text(["fixture"], [["high_u"]]), POWER_RULES, {"power": "probability"}, "Higher numerator df and stricter alpha fixture."),
            case("regression_f2_zero_effect", "degenerate_boundary", {"f2": 0.0, "u": 3, "v": 100, "alpha": 0.05},
                 csv_text(["fixture"], [["zero_effect"]]), POWER_RULES, {"power": "probability"}, "Zero effect must return the Type-I-error limit without NaN."),
            case("regression_f2_invalid_n", "expected_failure", {"f2": 0.15, "u": 10, "v": 0, "alpha": 0.05},
                 csv_text(["fixture"], [["invalid_df"]]), FAILURE_RULES, {}, "Zero denominator df must be rejected."),
        ],
    },
    "equivalence.tost.two_sample.v1": {
        "family": "equivalence",
        "primary": "r_base_tost_formula",
        "secondary": "scipy_t_cdf_formulas",
        "readme": "Independent base-R raw-scale two-sample TOST equations and a SciPy t-CDF implementation.",
        "evidence": ["G2", "G3", "G6", "G7"],
        "cases": [
            case("tost_two_sample_equivalence", "normal_typical", {"data": {"groupVar": "group", "outcomeVar": "val"}, "parameters": {"lowBound": -0.5, "highBound": 0.5, "alpha": 0.05, "varianceMethod": "student"}},
                 csv_text(["group", "val"], [["A", 10.1], ["A", 10.2], ["A", 9.9], ["A", 10.0], ["A", 10.1], ["B", 10.0], ["B", 10.1], ["B", 10.2], ["B", 9.8], ["B", 10.0]]), TOST_RULES, {"tost_results.p_lower": "probability", "tost_results.p_upper": "probability", "tost_results.tost_p": "probability"}, "Balanced raw-scale Student TOST fixture."),
            case("tost_unequal_n", "legal_complex", {"data": {"groupVar": "group", "outcomeVar": "val"}, "parameters": {"lowBound": -0.5, "highBound": 0.5, "alpha": 0.05, "varianceMethod": "welch"}},
                 csv_text(["group", "val"], [["A", 10.0], ["A", 10.5], ["A", 9.8], ["A", 10.2], ["A", 9.9], ["A", 10.3], ["B", 10.1], ["B", 10.4], ["B", 9.7], ["B", 10.2]]), TOST_RULES, {"tost_results.p_lower": "probability", "tost_results.p_upper": "probability", "tost_results.tost_p": "probability"}, "Unequal-n Welch TOST fixture with explicit df definition."),
            case("tost_bound_exact", "degenerate_boundary", {"data": {"groupVar": "group", "outcomeVar": "val"}, "parameters": {"lowBound": -0.3, "highBound": 0.3, "alpha": 0.05, "varianceMethod": "student"}},
                 csv_text(["group", "val"], [["A", 0.2], ["A", 0.3], ["A", 0.4], ["A", 0.3], ["B", 0.0], ["B", 0.0], ["B", 0.0], ["B", 0.0]]), TOST_RULES, {"tost_results.p_lower": "probability", "tost_results.p_upper": "probability", "tost_results.tost_p": "probability"}, "Mean difference equal to the upper equivalence bound; the strict decision must be false."),
            case("tost_invalid_bounds", "expected_failure", {"data": {"groupVar": "group", "outcomeVar": "val"}, "parameters": {"lowBound": 0.5, "highBound": -0.5, "alpha": 0.05, "varianceMethod": "student"}},
                 csv_text(["group", "val"], [["A", 1.0], ["A", 1.1], ["B", 1.0], ["B", 1.1]]), FAILURE_RULES, {}, "Reversed SESOI bounds must be rejected."),
        ],
    },
    "experiment.randomization.inference.v1": {
        "family": "experiment",
        "primary": "r_exact_enumeration",
        "secondary": "python_itertools_exact",
        "readme": "Independent R and Python exact assignment enumeration with fixed treatment counts per block.",
        "evidence": ["G1", "G3", "G6", "G7"],
        "cases": [
            case("randomization_inference_exact", "normal_typical", {"data": {"treatmentVar": "treatment", "outcomeVar": "outcome"}, "parameters": {"permutations": "exact", "testStatistic": "mean_difference"}},
                 csv_text(["treatment", "outcome"], [[1, 14.2], [1, 15.8], [1, 16.1], [1, 13.9], [0, 10.1], [0, 9.8], [0, 11.2], [0, 10.5]]), RANDOMIZATION_RULES, {"p_value_two_sided": "probability", "p_value_one_sided": "probability"}, "Unstratified exact complete-randomization fixture."),
            case("randomization_inference_stratified", "legal_complex", {"data": {"treatmentVar": "treatment", "outcomeVar": "outcome", "blockVar": "block"}, "parameters": {"permutations": "exact", "testStatistic": "mean_difference"}},
                 csv_text(["block", "treatment", "outcome"], [["A", 1, 12], ["A", 1, 14], ["A", 0, 8], ["A", 0, 9], ["B", 1, 15], ["B", 1, 16], ["B", 0, 11], ["B", 0, 10]]), RANDOMIZATION_RULES, {"p_value_two_sided": "probability", "p_value_one_sided": "probability"}, "Two strata with two treated observations per stratum."),
            case("randomization_inference_zero_diff", "degenerate_boundary", {"data": {"treatmentVar": "treatment", "outcomeVar": "outcome"}, "parameters": {"permutations": "exact", "testStatistic": "mean_difference"}},
                 csv_text(["treatment", "outcome"], [[1, 10], [1, 10], [0, 10], [0, 10]]), RANDOMIZATION_RULES, {"p_value_two_sided": "probability", "p_value_one_sided": "probability"}, "All assignment statistics equal zero."),
            case("randomization_inference_mismatched_assignment", "expected_failure", {"data": {"treatmentVar": "treatment", "outcomeVar": "outcome"}, "parameters": {"permutations": "exact", "testStatistic": "mean_difference", "assignmentLength": 3}},
                 csv_text(["treatment", "outcome"], [[1, 12], [1, 13], [0, 9], [0, 10]]), FAILURE_RULES, {}, "Declared assignment length differs from the input rows."),
        ],
    },
    "experiment.posthoc.games_howell.v1": {
        "family": "experiment",
        "primary": "r_studentized_range_games_howell",
        "secondary": "python_studentized_range",
        "readme": "Independent base-R and SciPy studentized-range Games--Howell references.",
        "evidence": ["G2", "G3", "G6", "G7"],
        "cases": [
            case("games_howell_unequal_var", "normal_typical", {"data": {"groupVar": "group", "outcomeVar": "score"}, "parameters": {"alpha": 0.05, "adjustment": "games_howell"}},
                 csv_text(["group", "score"], [["A", 12.5], ["A", 14.2], ["A", 11.8], ["A", 13.1], ["A", 12.9], ["B", 18.9], ["B", 24.3], ["B", 21.1], ["B", 19.8], ["B", 23.5], ["C", 15.1], ["C", 15.8], ["C", 16.2], ["C", 14.9], ["C", 15.5]]), GAMES_RULES, {"contrasts[0].p_adjusted": "probability", "contrasts[1].p_adjusted": "probability", "contrasts[2].p_adjusted": "probability"}, "Three-group unequal-variance fixture."),
            case("games_howell_unbalanced_n", "legal_complex", {"data": {"groupVar": "group", "outcomeVar": "score"}, "parameters": {"alpha": 0.05, "adjustment": "games_howell"}},
                 csv_text(["group", "score"], [["A", 10.0], ["A", 11.5], ["A", 9.5], ["B", 13.0], ["B", 14.0], ["B", 15.0], ["B", 12.0], ["B", 16.0], ["B", 14.5], ["C", 9.0], ["C", 10.0], ["C", 11.0], ["C", 12.0], ["C", 13.0], ["C", 9.0], ["C", 12.0], ["C", 13.0]]), GAMES_RULES, {"contrasts[0].p_adjusted": "probability", "contrasts[1].p_adjusted": "probability", "contrasts[2].p_adjusted": "probability"}, "Unequal sample sizes and heterogeneous variance with stable Welch degrees of freedom."),
            case("games_howell_zero_diff", "degenerate_boundary", {"data": {"groupVar": "group", "outcomeVar": "score"}, "parameters": {"alpha": 0.05, "adjustment": "games_howell"}},
                 csv_text(["group", "score"], [["A", 9], ["A", 10], ["A", 11], ["B", 9], ["B", 10], ["B", 11], ["C", 9], ["C", 10], ["C", 11]]), GAMES_RULES, {"contrasts[0].p_adjusted": "probability", "contrasts[1].p_adjusted": "probability", "contrasts[2].p_adjusted": "probability"}, "Equal group means with nonzero within-group variance."),
            case("games_howell_insufficient_sample", "expected_failure", {"data": {"groupVar": "group", "outcomeVar": "score"}, "parameters": {"alpha": 0.05, "adjustment": "games_howell"}},
                 csv_text(["group", "score"], [["A", 10], ["B", 11], ["B", 12]]), FAILURE_RULES, {}, "One group has fewer than two observations."),
        ],
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def materialize() -> None:
    for capability, matrix in MATRICES.items():
        bundle_dir = GOLDENS / capability
        write(
            bundle_dir / "bundle.yaml",
            yaml.safe_dump(
                {"schemaVersion": 1, "capabilityId": capability, "methodFamily": matrix["family"], "cases": [item["id"] for item in matrix["cases"]]},
                sort_keys=False, allow_unicode=True,
            ),
        )
        write(bundle_dir / "README.md", f"# {capability}\n\n{matrix['readme']}\n")
        for item in matrix["cases"]:
            case_dir = bundle_dir / "cases" / item["id"]
            data_path = case_dir / "data" / "input.csv"
            write(data_path, item["data"])
            rows = list(csv.reader(item["data"].splitlines()))
            dataset_hash = sha256(data_path)
            source = {
                "sourceId": f"synthetic_{item['id']}", "sourceType": "deterministic_parameter_fixture",
                "title": f"{item['id']} Golden Fixture", "publisher": "ResearchPath Golden Fixture Generator",
                "canonicalUrl": f"{REPO_URL}/tree/master/tests/goldens/{capability}",
                "retrievedAt": "2026-07-27T00:00:00Z", "version": "1.0.0", "license": "CC0-1.0",
                "sha256": dataset_hash, "authorityScore": 1.0, "executabilityScore": 1.0,
                "sourceTrustScore": 1.0, "recommendation": "Use only as a deterministic statistical Golden fixture",
                "allowedUse": "testing", "notes": item["source_note"],
            }
            write(case_dir / "data" / "source.json", json.dumps(source, indent=2, ensure_ascii=False) + "\n")
            write(case_dir / "data" / "LICENSE.txt", LICENSE)
            write(case_dir / "spec" / "analysis-spec.json", json.dumps(item["spec"], indent=2, ensure_ascii=False) + "\n")
            manifest = {
                "schemaVersion": 1,
                "identity": {"goldenCaseId": item["id"], "capabilityId": capability, "caseVersion": "1.0.0", "status": "draft"},
                "scenarioType": item["scenario"],
                "dataset": [{"path": "data/input.csv", "sha256": dataset_hash, "rowCount": len(rows) - 1, "columnCount": len(rows[0])}],
                "specPath": "spec/analysis-spec.json", "expectedOutputPath": "expected/expected.json",
                "primaryReference": {"engine": matrix["primary"], "version": "pinned", "command": "python reference/primary/run.py", "normalizedOutput": "reference/primary/normalized-output.json"},
                "secondaryReference": {"engine": matrix["secondary"], "version": "pinned", "command": "python reference/secondary/run.py", "normalizedOutput": "reference/secondary/normalized-output.json"},
                "comparisonRules": item["rules"], "evidenceLevels": matrix["evidence"],
                "evidence": {"sourceTrustMinimum": 0.85, "unresolvedConflicts": []},
            }
            write(case_dir / "manifest.yaml", yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True))
            write(case_dir / "reference" / "primary" / "run.py", PRIMARY_RUNNER)
            write(case_dir / "reference" / "secondary" / "run.py", SECONDARY_RUNNER)
            write(case_dir / "expected" / "expected.json", "{}\n")
            write(case_dir / "expected" / "invariants.json", json.dumps(item["invariants"], indent=2) + "\n")
            write(case_dir / "sut" / "run.py", SUT_RUNNER)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize audited foundational Golden matrices")
    parser.add_argument("--materialize", action="store_true", help="Write the reviewed deterministic fixture assets")
    args = parser.parse_args()
    if not args.materialize:
        parser.error("Refusing to modify Golden assets without --materialize")
    materialize()
    print(f"Materialized {len(MATRICES)} foundational Golden capability matrices.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
