from __future__ import annotations

import hashlib
import json
import math
import os
import runpy
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.services.repository_io import JsonObject
from app.settings import get_settings

SETTINGS = get_settings()
PROJECT_ROOT = SETTINGS.project_root
REFERENCE_DIR = PROJECT_ROOT / "apps" / "api" / "tests" / "fixtures" / "advanced" / "reference"
GOLDEN_DIR = REFERENCE_DIR.parent / "goldens"
ENGINE_PATH = PROJECT_ROOT / "engine" / "R" / "run_advanced_analysis.R"
GOLDEN_CASE_DIRS = tuple(
    sorted(
        case_dir
        for case_dir in (PROJECT_ROOT / "tests" / "goldens").glob("**/cases/*")
        if (case_dir / "manifest.yaml").is_file()
    )
)


def _load_json(path: Path) -> JsonObject:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_r(
    spec_name: str,
    data_name: str,
    *,
    mutate_spec: JsonObject | None = None,
) -> tuple[subprocess.CompletedProcess[str], JsonObject | None]:
    spec = _load_json(REFERENCE_DIR / spec_name)
    if mutate_spec:
        spec.update(mutate_spec)
    with tempfile.TemporaryDirectory() as temporary:
        temporary_path = Path(temporary)
        input_path = temporary_path / "input.json"
        output_path = temporary_path / "output.json"
        input_path.write_text(
            json.dumps(
                {
                    "spec": spec,
                    "dataPath": str(REFERENCE_DIR / data_name),
                    "artifactDirectory": str(temporary_path),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(SETTINGS.r_library_path)
        environment["LC_ALL"] = "English_United States.utf8"
        completed = subprocess.run(
            [
                str(SETTINGS.rscript_path),
                "--vanilla",
                str(ENGINE_PATH),
                str(input_path),
                str(output_path),
            ],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            env=environment,
            timeout=60,
        )
        output = _load_json(output_path) if output_path.is_file() else None
        return completed, output


def _assert_close(actual: object, expected: object, tolerance: float, label: str) -> None:
    assert isinstance(actual, (int, float)), f"{label} unexpectedly missing"
    assert isinstance(expected, (int, float)), f"{label} golden is not numeric"
    assert math.isclose(float(actual), float(expected), rel_tol=tolerance, abs_tol=tolerance), (
        f"{label}: expected {expected}, got {actual}"
    )


def _by_key(rows: list[JsonObject], key: str) -> dict[str, JsonObject]:
    return {str(row[key]): row for row in rows}


@pytest.mark.parametrize(
    ("golden_name", "data_name"),
    [
        ("obrien-kaiser-phase.expected.json", "obrien-kaiser-phase.csv"),
        ("toothgrowth-factorial.expected.json", "toothgrowth-factorial.csv"),
        ("moore-ancova.expected.json", "moore-ancova.csv"),
        ("sleepstudy-random-slope.expected.json", "sleepstudy.csv"),
        (
            "sleepstudy-centered-unbalanced.expected.json",
            "sleepstudy-centered-unbalanced.csv",
        ),
        ("demo-growth-fiml.expected.json", "demo-growth-fiml-attrition.csv"),
        (
            "demo-growth-fiml-nonmonotone.expected.json",
            "demo-growth-fiml-nonmonotone.csv",
        ),
    ],
)
def test_reference_fixture_sha256_is_bound_to_golden(golden_name: str, data_name: str) -> None:
    golden = _load_json(GOLDEN_DIR / golden_name)
    assert _sha256(REFERENCE_DIR / data_name) == golden["provenance"]["datasetSha256"]
    assert golden["provenance"]["reference"].startswith("Independent ")
    assert golden["provenance"]["comparisonFields"]


def test_obrien_kaiser_greenhouse_geisser_emm_and_ci_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "obrien-kaiser-phase.expected.json")
    completed, actual = _run_r("obrien-kaiser-phase.spec.json", "obrien-kaiser-phase.csv")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    tolerance = golden["provenance"]["tolerance"]
    expected_family = golden["familyResult"]
    actual_family = actual["familyResult"]

    expected_omnibus = _by_key(expected_family["omnibusTests"], "term")
    actual_omnibus = _by_key(actual_family["omnibusTests"], "term")
    assert actual_omnibus.keys() == expected_omnibus.keys()
    for term, expected in expected_omnibus.items():
        current = actual_omnibus[term]
        for actual_key, expected_key in (
            ("numeratorDf", "num Df"),
            ("denominatorDf", "den Df"),
            ("f", "F"),
            ("pValue", "Pr(>F)"),
            ("partialEtaSquared", "pes"),
        ):
            _assert_close(
                current[actual_key],
                expected[expected_key],
                tolerance["omnibus"],
                f"{term}.{actual_key}",
            )

    assert actual_family["sphericity"]["selectedCorrection"] == "GG"
    assert actual_family["sphericity"]["primaryInference"] == actual_family["omnibusTests"]
    expected_corrections = expected_family["sphericity"]["corrections"]
    actual_corrections = actual_family["sphericity"]["corrections"]
    assert len(actual_corrections) == len(expected_corrections)
    for index, expected in enumerate(expected_corrections):
        for key, value in expected.items():
            if isinstance(value, (int, float)):
                _assert_close(
                    actual_corrections[index][key],
                    value,
                    tolerance["epsilon"],
                    f"sphericity[{index}].{key}",
                )

    for section, numeric_fields, tolerance_key in (
        (
            "estimatedMarginalMeans",
            ("emmean", "SE", "df", "lower.CL", "upper.CL"),
            "emm",
        ),
        (
            "contrasts",
            ("estimate", "SE", "df", "lower.CL", "upper.CL", "t.ratio", "p.value"),
            "contrast",
        ),
    ):
        expected_rows = expected_family[section]
        actual_rows = actual_family[section]
        assert len(actual_rows) == len(expected_rows)
        for index, expected in enumerate(expected_rows):
            for key in numeric_fields:
                _assert_close(
                    actual_rows[index][key],
                    expected[key],
                    tolerance[tolerance_key],
                    f"{section}[{index}].{key}",
                )

    assert all(
        row["lower.CL"] < row["emmean"] < row["upper.CL"]
        for row in actual_family["estimatedMarginalMeans"]
    )


@pytest.mark.parametrize(
    ("spec_name", "data_name", "golden_name"),
    [
        (
            "toothgrowth-factorial.spec.json",
            "toothgrowth-factorial.csv",
            "toothgrowth-factorial.expected.json",
        ),
        ("moore-ancova.spec.json", "moore-ancova.csv", "moore-ancova.expected.json"),
    ],
)
def test_public_between_subject_experimental_gold_standards(
    spec_name: str, data_name: str, golden_name: str
) -> None:
    golden = _load_json(GOLDEN_DIR / golden_name)
    completed, actual = _run_r(spec_name, data_name)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    tolerance = golden["provenance"]["tolerance"]
    expected_family = golden["familyResult"]
    actual_family = actual["familyResult"]

    expected_omnibus = _by_key(expected_family["omnibusTests"], "term")
    actual_omnibus = _by_key(actual_family["omnibusTests"], "term")
    assert actual_omnibus.keys() == expected_omnibus.keys()
    for term, expected in expected_omnibus.items():
        for actual_key, expected_key in (
            ("numeratorDf", "num Df"),
            ("denominatorDf", "den Df"),
            ("f", "F"),
            ("pValue", "Pr(>F)"),
            ("partialEtaSquared", "pes"),
        ):
            _assert_close(
                actual_omnibus[term][actual_key],
                expected[expected_key],
                tolerance["omnibus"],
                f"{golden_name}:{term}.{actual_key}",
            )

    for section, numeric_fields, tolerance_key in (
        ("estimatedMarginalMeans", ("emmean", "SE", "df", "lower.CL", "upper.CL"), "emm"),
        (
            "contrasts",
            ("estimate", "SE", "df", "lower.CL", "upper.CL", "t.ratio", "p.value"),
            "contrast",
        ),
    ):
        expected_rows = expected_family[section]
        actual_rows = actual_family[section]
        assert len(actual_rows) == len(expected_rows)
        for index, expected in enumerate(expected_rows):
            for key in numeric_fields:
                _assert_close(
                    actual_rows[index][key],
                    expected[key],
                    tolerance[tolerance_key],
                    f"{golden_name}:{section}[{index}].{key}",
                )


def test_sleepstudy_multilevel_random_slope_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "sleepstudy-random-slope.expected.json")
    completed, actual = _run_r("sleepstudy-random-slope.spec.json", "sleepstudy.csv")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    tolerance = golden["provenance"]["tolerance"]
    expected_family = golden["familyResult"]
    actual_family = actual["familyResult"]
    expected_fixed = _by_key(expected_family["fixedEffects"], "term")
    actual_fixed = _by_key(actual_family["fixedEffects"], "term")
    assert actual_fixed.keys() == expected_fixed.keys()
    for term, expected in expected_fixed.items():
        for key in ("Estimate", "Std. Error", "df", "t value", "Pr(>|t|)"):
            _assert_close(
                actual_fixed[term][key],
                expected[key],
                tolerance["fixedEffect"],
                f"{term}.{key}",
            )

    for index, expected in enumerate(expected_family["varianceComponents"]):
        for key in ("vcov", "sdcor"):
            _assert_close(
                actual_family["varianceComponents"][index][key],
                expected[key],
                tolerance["varianceComponent"],
                f"varianceComponents[{index}].{key}",
            )
    for key in ("AIC", "BIC", "logLik"):
        _assert_close(
            actual_family["fitIndices"][key],
            expected_family["fitIndices"][key],
            tolerance["fitIndex"],
            f"fitIndices.{key}",
        )
    assert actual["sampleFlow"]["clusters"] == 18
    assert {warning["code"] for warning in actual["warnings"]} == {"FEW_CLUSTERS"}


def test_sleepstudy_kenward_roger_degrees_of_freedom_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "sleepstudy-random-slope.expected.json")
    completed, actual = _run_r(
        "sleepstudy-random-slope.spec.json",
        "sleepstudy.csv",
        mutate_spec={"degreesOfFreedom": "kenward_roger"},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    expected_fixed = _by_key(golden["familyResult"]["kenwardRogerFixedEffects"], "term")
    actual_fixed = _by_key(actual["familyResult"]["fixedEffects"], "term")
    tolerance = golden["provenance"]["tolerance"]["fixedEffect"]
    for term, expected in expected_fixed.items():
        for key in ("Estimate", "Std. Error", "df", "t value", "Pr(>|t|)"):
            _assert_close(actual_fixed[term][key], expected[key], tolerance, f"KR:{term}.{key}")
    assert actual["provenance"]["degreesOfFreedomMethod"] == "kenward_roger"


def test_unbalanced_group_mean_centering_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "sleepstudy-centered-unbalanced.expected.json")
    completed, actual = _run_r(
        "sleepstudy-centered-unbalanced.spec.json",
        "sleepstudy-centered-unbalanced.csv",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    expected_fixed = _by_key(golden["familyResult"]["fixedEffects"], "term")
    actual_fixed = _by_key(actual["familyResult"]["fixedEffects"], "term")
    tolerance = golden["provenance"]["tolerance"]["fixedEffect"]
    assert set(actual["familyResult"]["compiledFixedEffectIds"]) == {"Days", "Days__between"}
    for term, expected in expected_fixed.items():
        for key in ("Estimate", "Std. Error", "df", "t value", "Pr(>|t|)"):
            _assert_close(
                actual_fixed[term][key],
                expected[key],
                tolerance,
                f"centered:{term}.{key}",
            )
    cluster_sizes = [int(value) for value in golden["clusterSizes"].values()]
    assert min(cluster_sizes) < max(cluster_sizes)
    assert "MISSING_BETWEEN_EFFECT" not in {warning["code"] for warning in actual["warnings"]}


def test_lavaan_fiml_attrition_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "demo-growth-fiml.expected.json")
    completed, actual = _run_r("demo-growth-fiml.spec.json", "demo-growth-fiml-attrition.csv")
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    tolerance = golden["provenance"]["tolerance"]
    expected_family = golden["familyResult"]
    actual_family = actual["familyResult"]
    assert actual["sampleFlow"]["original"] == 400
    assert actual["sampleFlow"]["included"] == 400
    assert actual["sampleFlow"]["excluded"] == 0
    assert actual["sampleFlow"]["missingMethod"] == "fiml"

    expected_parameters = {
        f"{row['lhs']}~{row['rhs']}": row for row in expected_family["parameters"]
    }
    actual_parameters = {f"{row['lhs']}~{row['rhs']}": row for row in actual_family["parameters"]}
    assert actual_parameters.keys() == expected_parameters.keys()
    for parameter, expected in expected_parameters.items():
        for key in ("est", "se", "z", "pvalue", "ci.lower", "ci.upper"):
            _assert_close(
                actual_parameters[parameter][key],
                expected[key],
                tolerance["parameter"],
                f"{parameter}.{key}",
            )
    for key, expected in expected_family["fitIndices"].items():
        _assert_close(
            actual_family["fitIndices"][key],
            expected,
            tolerance["fitIndex"],
            f"fitIndices.{key}",
        )

    expected_flow = expected_family["waveSampleFlow"]
    actual_flow = actual_family["waveSampleFlow"]
    assert [row["observed"] for row in actual_flow] == [400, 400, 360, 300]
    assert [row["attritionFromPrevious"] for row in actual_flow] == [0, 0, 40, 60]
    assert [row["reenteredFromPrevious"] for row in actual_flow] == [0, 0, 0, 0]
    assert [row["observed"] for row in actual_flow] == [row["observed"] for row in expected_flow]
    assert (
        len(json.loads(actual_family["missingPatterns"])) == expected_family["missingPatternCount"]
    )


def test_lavaan_fiml_nonmonotone_attrition_and_reentry_gold_standard() -> None:
    golden = _load_json(GOLDEN_DIR / "demo-growth-fiml-nonmonotone.expected.json")
    completed, actual = _run_r(
        "demo-growth-fiml-nonmonotone.spec.json",
        "demo-growth-fiml-nonmonotone.csv",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert actual is not None
    expected_family = golden["familyResult"]
    actual_family = actual["familyResult"]
    tolerance = golden["provenance"]["tolerance"]
    assert actual["sampleFlow"]["included"] == 400
    assert [row["observed"] for row in actual_family["waveSampleFlow"]] == expected_family[
        "waveObserved"
    ]
    assert [
        row["attritionFromPrevious"] for row in actual_family["waveSampleFlow"]
    ] == expected_family["attritionFromPrevious"]
    assert [
        row["reenteredFromPrevious"] for row in actual_family["waveSampleFlow"]
    ] == expected_family["reenteredFromPrevious"]
    expected_parameters = {
        f"{row['lhs']}~{row['rhs']}": row for row in expected_family["parameters"]
    }
    actual_parameters = {f"{row['lhs']}~{row['rhs']}": row for row in actual_family["parameters"]}
    for parameter, expected in expected_parameters.items():
        for key in ("est", "se", "z", "pvalue", "ci.lower", "ci.upper"):
            _assert_close(
                actual_parameters[parameter][key],
                expected[key],
                tolerance["parameter"],
                f"reentry:{parameter}.{key}",
            )
    assert (
        len(json.loads(actual_family["missingPatterns"])) == expected_family["missingPatternCount"]
    )


def test_observed_growth_distinguishes_available_rows_from_complete_cases() -> None:
    available_completed, available = _run_r(
        "demo-growth-fiml.spec.json",
        "demo-growth-fiml-attrition.csv",
        mutate_spec={"modelType": "growth_curve", "missing": "available_rows_ml"},
    )
    complete_completed, complete = _run_r(
        "demo-growth-fiml.spec.json",
        "demo-growth-fiml-attrition.csv",
        mutate_spec={"modelType": "growth_curve", "missing": "complete_cases"},
    )
    assert available_completed.returncode == 0, (
        available_completed.stdout + available_completed.stderr
    )
    assert complete_completed.returncode == 0, complete_completed.stdout + complete_completed.stderr
    assert available is not None and complete is not None
    assert available["sampleFlow"]["included"] == 400
    assert available["sampleFlow"]["missingMethod"] == "available_rows_ml"
    assert complete["sampleFlow"]["included"] == 300
    assert complete["sampleFlow"]["missingMethod"] == "complete_cases"


@pytest.mark.golden
@pytest.mark.parametrize("case_dir", GOLDEN_CASE_DIRS, ids=lambda path: path.name)
def test_golden_bundle_static_verification(case_dir: Path) -> None:
    """Validate one frozen reference and its metamorphic invariants."""
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    import tools.goldens.invariants  # pyright: ignore[reportMissingImports]
    import tools.goldens.verify  # pyright: ignore[reportMissingImports]

    evaluate_metamorphic_invariants_for_case = (
        tools.goldens.invariants.evaluate_metamorphic_invariants_for_case
    )
    verify_case_manifest = tools.goldens.verify.verify_case_manifest

    assert len(GOLDEN_CASE_DIRS) >= 26, (
        f"Expected at least 26 golden cases in {PROJECT_ROOT / 'tests' / 'goldens'}"
    )
    result = verify_case_manifest(case_dir)
    assert result.passed, f"Golden bundle verification failed for {case_dir.name}: {result.failures}"

    inv_res = evaluate_metamorphic_invariants_for_case(case_dir)
    has_reference_runner = (case_dir / "reference" / "primary" / "run.py").is_file()
    assert not inv_res["passed"] or has_reference_runner
    if not has_reference_runner:
        assert any("not executed" in detail for detail in inv_res["details"])


def test_sut_runner_refuses_reference_copy_fallback(tmp_path: Path) -> None:
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.sut_runner import run_sut_for_case  # pyright: ignore[reportMissingImports]

    case_dir = tmp_path / "case"
    (case_dir / "reference" / "primary").mkdir(parents=True)
    (case_dir / "expected").mkdir()
    (case_dir / "sut").mkdir()
    (case_dir / "manifest.yaml").write_text("schemaVersion: 1\n", encoding="utf-8")
    (case_dir / "reference" / "primary" / "normalized-output.json").write_text(
        '{"estimate": 1}\n', encoding="utf-8"
    )
    (case_dir / "expected" / "expected.json").write_text(
        '{"estimate": 1}\n', encoding="utf-8"
    )
    existing_sut = case_dir / "sut" / "normalized-output.json"
    existing_sut.write_text('{"estimate": 999}\n', encoding="utf-8")

    ok, message = run_sut_for_case(case_dir)

    assert not ok
    assert "sut/run.py is missing" in message
    assert _load_json(existing_sut) == {"estimate": 999}


def test_strict_sut_verification_rejects_unattested_checked_in_output(tmp_path: Path) -> None:
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.verify import verify_case_manifest  # pyright: ignore[reportMissingImports]

    source_case = (
        PROJECT_ROOT
        / "tests"
        / "goldens"
        / "imputation.pooling.linear.rubin.v1"
        / "cases"
        / "rubin_standard"
    )
    case_dir = tmp_path / "rubin_standard"
    shutil.copytree(source_case, case_dir)
    (case_dir / "sut" / "provenance.json").unlink()
    result = verify_case_manifest(case_dir, require_sut=True)

    assert not result.passed
    assert any(failure.path == "sut/provenance.json" for failure in result.failures)


def test_reference_builder_does_not_count_preserved_asset_as_execution(tmp_path: Path) -> None:
    module = runpy.run_path(str(PROJECT_ROOT / "tools" / "goldens" / "build-references.py"))
    case_dir = tmp_path / "case"
    (case_dir / "reference" / "primary").mkdir(parents=True)
    (case_dir / "reference" / "primary" / "normalized-output.json").write_text(
        '{"estimate": 1}\n', encoding="utf-8"
    )
    (case_dir / "manifest.yaml").write_text(
        "primaryReference:\n  normalizedOutput: reference/primary/normalized-output.json\n",
        encoding="utf-8",
    )
    result = module["build_references_for_case"](case_dir, use_docker_if_avail=False)

    assert not result["passed"]
    assert not result["primaryExecuted"]
    assert result["reason"] == "Primary reference command is missing"


def test_comparator_rejects_non_finite_and_invalid_set_shapes() -> None:
    import sys

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from tools.goldens.schema import ComparatorKind  # pyright: ignore[reportMissingImports]
    from tools.goldens.verify import compare_value  # pyright: ignore[reportMissingImports]

    finite_ok, _ = compare_value(
        float("nan"), 1.0, ComparatorKind.ABSOLUTE_RELATIVE, 1e-5, 1e-4
    )
    shape_ok, _ = compare_value(
        [1.0, 2.0], [1.0, 2.0], ComparatorKind.SET_EQUIVALENT, 1e-5, 1e-4
    )
    aligned_ok, _ = compare_value(
        [[-0.2, 0.8], [-0.9, 0.1]],
        [[0.8, 0.2], [0.1, 0.9]],
        ComparatorKind.SET_EQUIVALENT,
        1e-8,
        1e-8,
    )

    assert not finite_ok
    assert not shape_ok
    assert aligned_ok
