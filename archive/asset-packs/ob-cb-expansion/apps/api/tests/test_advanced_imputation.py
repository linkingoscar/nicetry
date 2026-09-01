import json
import os
import subprocess
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
    import tempfile

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
