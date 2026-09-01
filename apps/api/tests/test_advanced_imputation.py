import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.advanced_contracts import (
    ImputationVariable,
    MultipleImputationSpec,
    PassiveRule,
    PooledAnalysisSpec,
)
from app.settings import get_settings


def test_mi_accepts_restricted_passive_product_rule():
    spec = MultipleImputationSpec(
        analysis_id="test",
        name="test",
        dataset_version_id="dataset1",
        family="multiple_imputation",
        method="mice_fcs",
        imputations=5,
        iterations=5,
        variables=[ImputationVariable(variable_id="v1", method="pmm", predictor_ids=["v2"])],
        passive_rules=[PassiveRule(target_variable_id="interaction", expression="v1 * v2")],
        pooling="none",
    )
    assert spec.passive_rules[0].expression == "v1 * v2"


def test_mi_rejects_unsafe_passive_expression():
    with pytest.raises(ValueError, match="PASSIVE_EXPRESSION_NOT_SUPPORTED"):
        PassiveRule(target_variable_id="v1", expression="v2+1")


def test_mi_rejects_joint_model():
    with pytest.raises(ValueError, match="JOINT_MODEL_NOT_SUPPORTED"):
        MultipleImputationSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="multiple_imputation",
            method="joint_model",
            imputations=5,
            iterations=5,
            variables=[ImputationVariable(variable_id="v1", method="pmm", predictor_ids=["v2"])],
            pooling="none",
        )


def test_mi_validates_two_level_requires_cluster():
    with pytest.raises(ValueError, match="两层插补方法必须指定 clusterVariableId"):
        MultipleImputationSpec(
            analysis_id="test",
            name="test",
            dataset_version_id="dataset1",
            family="multiple_imputation",
            method="mice_fcs",
            imputations=5,
            iterations=5,
            variables=[
                ImputationVariable(
                    variable_id="v1", method="two_level_normal", predictor_ids=["v2"]
                )
            ],
            pooling="none",
        )


def test_mi_accepts_rubin_linear_regression_pooling():
    spec = MultipleImputationSpec(
        analysis_id="test_rubin_01",
        name="test",
        dataset_version_id="dataset1",
        family="multiple_imputation",
        method="mice_fcs",
        imputations=5,
        iterations=5,
        variables=[ImputationVariable(variable_id="v01", method="pmm", predictor_ids=["v02"])],
        pooling="rubin",
        pooled_analysis=PooledAnalysisSpec(outcome_id="v01", predictor_ids=["v02"]),
    )
    assert spec.pooling == "rubin"


def test_mi_rejects_imputation_model_that_omits_substantive_model_variable():
    with pytest.raises(ValueError, match="MI_IMPUTATION_MODEL_INCOMPATIBLE"):
        MultipleImputationSpec(
            analysis_id="test_incompatible_mi",
            name="test",
            dataset_version_id="dataset1",
            family="multiple_imputation",
            method="mice_fcs",
            imputations=5,
            iterations=5,
            variables=[
                ImputationVariable(
                    variable_id="predictor_x",
                    method="pmm",
                    predictor_ids=["outcome_y"],
                ),
                ImputationVariable(
                    variable_id="covariate_z",
                    method="pmm",
                    predictor_ids=["outcome_y", "predictor_x"],
                ),
            ],
            pooling="rubin",
            pooled_analysis=PooledAnalysisSpec(
                outcome_id="outcome_y",
                predictor_ids=["predictor_x", "covariate_z"],
            ),
        )


def test_mi_records_and_rejects_stale_substantive_model_hash():
    spec = MultipleImputationSpec(
        family="multiple_imputation",
        analysis_id="mi_hash",
        name="MI hash",
        dataset_version_id="dataset_123",
        variables=[
            ImputationVariable(variable_id="outcome", predictor_ids=["predictor"]),
            ImputationVariable(variable_id="predictor", predictor_ids=["outcome"]),
        ],
        pooling="rubin",
        pooled_analysis=PooledAnalysisSpec(
            outcome_id="outcome", predictor_ids=["predictor"]
        ),
    )
    assert spec.substantive_model_hash is not None
    assert len(spec.substantive_model_hash) == 64

    with pytest.raises(ValueError, match="MI_SUBSTANTIVE_MODEL_CHANGED_REIMPUTE_REQUIRED"):
        MultipleImputationSpec(
            family="multiple_imputation",
            analysis_id="mi_hash_stale",
            name="MI hash stale",
            dataset_version_id="dataset_123",
            variables=[
                ImputationVariable(variable_id="outcome", predictor_ids=["predictor"]),
                ImputationVariable(variable_id="predictor", predictor_ids=["outcome"]),
            ],
            pooling="rubin",
            pooled_analysis=PooledAnalysisSpec(
                outcome_id="outcome", predictor_ids=["predictor"]
            ),
            substantive_model_hash="0" * 64,
        )


def test_mi_r_runner_returns_nonempty_rubin_pooling() -> None:
    settings = get_settings()
    project_root = settings.project_root
    spec_path = (
        project_root / "apps/api/tests/fixtures/advanced/imputation/mar-known-parameters.spec.json"
    )
    data_path = (
        project_root / "apps/api/tests/fixtures/advanced/imputation/mar-known-parameters.csv"
    )
    runner = project_root / "engine/R/run_advanced_analysis.R"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        input_path = root / "input.json"
        output_path = root / "output.json"
        input_path.write_text(
            json.dumps(
                {"spec": spec, "dataPath": str(data_path), "artifactDirectory": str(root)},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(runner),
                str(input_path),
                str(output_path),
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )
        result = (
            json.loads(output_path.read_text(encoding="utf-8")) if output_path.is_file() else None
        )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert result is not None
    assert result["familyResult"]["poolingStatus"] == "rubin"
    assert result["familyResult"]["pooledAnalysis"]["estimates"]
    assert len(result["familyResult"]["pooledAnalysis"]["substantiveModelHash"]) == 64
    assert result["familyResult"]["trace"]
    assert result["familyResult"]["distribution"]
    assert {row["term"] for row in result["familyResult"]["fractionMissingInformation"]} == {
        "(Intercept)",
        "x",
        "z",
    }
    assert {row["term"] for row in result["familyResult"]["pooledAnalysis"]["estimates"]} == {
        "(Intercept)",
        "x",
        "z",
    }


def test_mi_accepts_valid_config():
    spec = MultipleImputationSpec(
        analysis_id="test",
        name="test",
        dataset_version_id="dataset1",
        family="multiple_imputation",
        method="mice_fcs",
        imputations=10,
        iterations=10,
        variables=[ImputationVariable(variable_id="v1", method="pmm", predictor_ids=["v2"])],
        pooling="none",
    )
    assert spec.imputations == 10


def test_imputation_runner_reports_missing_columns_before_calling_mice() -> None:
    settings = get_settings()
    project_root = settings.project_root
    spec_path = (
        project_root / "apps/api/tests/fixtures/advanced/imputation/mar-known-parameters.spec.json"
    )
    data_path = (
        project_root / "apps/api/tests/fixtures/advanced/imputation/mar-known-parameters.csv"
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec["variables"][0]["predictorIds"] = ["missing_predictor"]
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        input_path = work / "input.json"
        output_path = work / "output.json"
        input_path.write_text(
            json.dumps({"spec": spec, "dataPath": str(data_path), "artifactDirectory": str(work)}),
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["R_LIBS_USER"] = str(settings.r_library_path)
        completed = subprocess.run(
            [
                str(settings.rscript_path),
                "--vanilla",
                str(project_root / "engine/R/run_advanced_analysis.R"),
                str(input_path),
                str(output_path),
            ],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
        )

    assert completed.returncode != 0
    assert "MI_COLUMN_NOT_FOUND: missing_predictor" in completed.stderr
