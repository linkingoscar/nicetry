from __future__ import annotations

import json
import time
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pytest
from _sem_calculations_helpers import _ensure_independent_context, _sem_spec
from starlette.testclient import TestClient

from app.main import app

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


SEM_REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "sem-numeric-reference-v1.json").read_text(encoding="utf-8")
)


def _assert_sem_numeric_reference(
    sem_result: dict, reference_key: str, *, executed_estimator: str | None = None
) -> None:
    reference = SEM_REFERENCE[reference_key]
    tolerance = SEM_REFERENCE["absoluteTolerance"]
    for key, expected in reference["fit"].items():
        assert sem_result["fitIndices"][key] == pytest.approx(expected, abs=tolerance)
    assert [item["stdAll"] for item in sem_result["loadings"]] == pytest.approx(
        reference["loadingStdAll"], abs=tolerance
    )
    assert [item["estimate"] for item in sem_result["paths"]] == pytest.approx(
        reference["pathEstimates"], abs=tolerance
    )
    execution = sem_result["numericReferenceMatrix"]["execution"]
    assert execution["fixtureId"] == SEM_REFERENCE["fixtureId"]
    assert execution["executedEstimator"] == (executed_estimator or reference_key)


def _await_analysis(response, timeout: float = 120.0) -> dict:
    assert response.status_code == 202, response.text
    run_id = response.json()["id"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state_response = client.get(f"/api/v1/analyses/{run_id}")
        assert state_response.status_code == 200, state_response.text
        state = state_response.json()
        if state["status"] in {"succeeded", "failed", "cancelled"}:
            if state["status"] != "succeeded":
                import json

                print("JOB FAILED STATE:", json.dumps(state, indent=2))
            assert state["status"] == "succeeded", state
            res_response = client.get(f"/api/v1/analyses/{run_id}/result")
            assert res_response.status_code == 200, res_response.text
            state["result"] = res_response.json()
            return state
        time.sleep(0.05)
    raise AssertionError(f"分析任务 {run_id} 未在 {timeout} 秒内完成")


def _model_dataset(with_missing: bool = False) -> tuple[dict, dict]:
    # 使用 numpy 生成符合真实协方差结构且不共线的模拟数据
    rng = np.random.default_rng(42)
    n = 300

    # 模拟潜在因子
    f1 = rng.normal(0, 1, n)
    f2 = 0.5 * f1 + rng.normal(0, 0.8, n)
    f3 = 0.6 * f2 + rng.normal(0, 0.8, n)

    # 转换为 1-5 的 Likert 题项 (带有一些噪声以防共线性，标准差 1.0)
    x1 = np.clip(np.round(3 + f1 + rng.normal(0, 1.0, n)), 1, 5).astype(int)
    x2 = np.clip(np.round(3 + 0.8 * f1 + rng.normal(0, 1.0, n)), 1, 5).astype(int)

    m1 = np.clip(np.round(3 + f2 + rng.normal(0, 1.0, n)), 1, 5).astype(int)
    m2 = np.clip(np.round(3 + 0.8 * f2 + rng.normal(0, 1.0, n)), 1, 5).astype(int)

    y1 = np.clip(np.round(3 + f3 + rng.normal(0, 1.0, n)), 1, 5).astype(int)
    y2 = np.clip(np.round(3 + 0.8 * f3 + rng.normal(0, 1.0, n)), 1, 5).astype(int)

    # 协变量与分组变量
    age = np.round(25 + 5 * f1 + rng.normal(0, 3, n)).astype(int)
    group = np.where(rng.normal(0, 1, n) > 0, "A", "B")

    columns = ["respondent_id", "x1", "x2", "m1", "m2", "y1", "y2", "group", "age"]
    rows = [",".join(columns)]
    for i in range(n):
        values = [i + 1, x1[i], x2[i], m1[i], m2[i], y1[i], y2[i], group[i], age[i]]
        if with_missing:
            # Planned item-level missingness: every row retains information,
            # but listwise deletion would still discard 10% of the sample.
            if i % 10 == 0:
                values[1] = ""
        rows.append(",".join(str(value) for value in values))

    payload = ("\n".join(rows) + "\n").encode("utf-8")
    imported = client.post(
        "/api/v1/datasets/import",
        files={"file": ("sem_test.csv", BytesIO(payload), "text/csv")},
    )
    assert imported.status_code == 201, imported.text
    dataset = imported.json()
    updates = [
        {
            "id": variable["id"],
            "confirmed_type": (
                "id"
                if variable["originalName"] == "respondent_id"
                else "binary"
                if variable["originalName"] == "group"
                else "ordinal"
                if variable["originalName"] in {"x1", "x2", "m1", "m2", "y1", "y2"}
                else "continuous"
            ),
        }
        for variable in dataset["variables"]
    ]
    confirmed = client.put(
        f"/api/v1/datasets/{dataset['id']}/dictionary",
        json={"variables": updates},
    )
    assert confirmed.status_code == 200
    dataset = confirmed.json()

    # 构筑测量模型
    item_ids = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    constructs = []
    for role in ("x", "m", "y"):
        constructs.append(
            {
                "id": f"construct_{role}",
                "name": role.upper(),
                "item_ids": [item_ids[f"{role}1"], item_ids[f"{role}2"]],
                "reverse_item_ids": [],
                "theoretical_minimum": 1,
                "theoretical_maximum": 5,
                "aggregation": "mean",
                "minimum_valid_proportion": 0.8,
            }
        )
    measured = client.put(
        f"/api/v1/datasets/{dataset['id']}/measurement",
        json={"constructs": constructs},
    )
    assert measured.status_code == 200, measured.text
    _ensure_independent_context(dataset)
    return dataset, measured.json()


def test_sem_model_validation_and_ml_execution() -> None:
    dataset, measurement = _model_dataset()
    model = _sem_spec(dataset, measurement, estimator="ML")
    model["estimation"]["multiGroup"] = {
        "compareStructuralPaths": True,
        "estimateLatentMeans": True,
        "partialInvarianceReleases": [
            {
                "stage": "metric",
                "constraint": "loading",
                "latentId": "latent_f1",
                "indicatorId": model["latents"][0]["indicators"][1],
                "rationale": "预设检验该题项在组间措辞语境不同。",
            }
        ],
    }

    # 1. 验证模型语义与规范性
    validate_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/validate",
        json={"model_spec": model},
    )
    assert validate_response.status_code == 200, validate_response.text
    validation = validate_response.json()
    assert validation["valid"] is True, validation["errors"]
    assert validation["template"] == "sem"

    # 2. 冻结模型版本
    freeze_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert freeze_response.status_code == 200, freeze_response.text
    frozen = freeze_response.json()
    assert frozen["status"] == "frozen"

    # 3. 运行 SEM 分析并等待结果
    analysis_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen['version']}/analysis"
    )
    state = _await_analysis(analysis_response)
    result = state["result"]

    # 4. 断言结果结构是否符合 ResultBundle 0.3.0
    assert result["jobStatus"] == "completed"
    assert result["estimationStatus"] == "succeeded"
    assert result["inferenceStatus"] == "reliable"
    assert result["publicationEligibility"] == "conditional"
    assert result["run"]["template"] == "sem"
    assert "semResult" in result
    assert "invarianceResult" in result

    # 验证主估计值
    sem_res = result["semResult"]
    assert "fitIndices" in sem_res
    assert sem_res["fitIndices"]["cfi"] > 0.0
    assert len(sem_res["loadings"]) == 6
    assert (
        len(sem_res["paths"]) == 4
    )  # latent_f1->latent_f2, latent_f2->latent_f3 + 2 自动投影的控制变量 paths (age->latent_f2, age->latent_f3)
    assert len(sem_res["reliability"]) == 3
    assert sem_res["publicationEligible"] is True
    assert sem_res["requiresManualReview"] is False
    assert "continuous" in sem_res["numericReferenceMatrix"]
    assert "ordinal" in sem_res["numericReferenceMatrix"]
    assert result["claimBoundary"]["claimMode"] == "association"
    assert result["claimBoundary"]["causalLanguageAllowed"] is False
    assert result["provenance"]["estimator"] == "ML"
    assert result["provenance"]["missingMethodExecuted"] == "listwise"

    for rel in sem_res["reliability"]:
        assert rel["compositeReliability"] > 0
        assert rel["ave"] > 0

    # 验证多组分析与等值性
    inv_res = result["invarianceResult"]
    assert len(inv_res["models"]) == 4
    assert len(inv_res["comparisons"]) == 3
    for comp in inv_res["comparisons"]:
        assert "invarianceHolds" in comp
        assert comp["deltaChiSquare"] >= 0
    assert {group["group"] for group in inv_res["groupParameters"]} == {"A", "B"}
    assert all(group["paths"] for group in inv_res["groupParameters"])
    assert inv_res["latentMeans"]
    assert inv_res["structuralComparison"]["model"] == "structural"
    assert len(inv_res["pathComparisons"]) == 4
    assert all(
        comparison["ciLower"] <= comparison["difference"] <= comparison["ciUpper"]
        for comparison in inv_res["pathComparisons"]
    )
    assert inv_res["partialInvarianceReleases"][0]["lavaanParameters"]
    metric = next(model for model in inv_res["models"] if model["model"] == "metric")
    assert metric["releasedParameters"]
    assert "表：多群组测量等值性检验" in result["apaTables"]
    assert "表：结构路径跨组差异" in result["apaTables"]
    export = client.get(f"/api/v1/analyses/{state['id']}/export")
    assert export.status_code == 200, export.text
    with zipfile.ZipFile(BytesIO(export.content)) as archive:
        apa_path = next(name for name in archive.namelist() if name.endswith("report/apa-tables.md"))
        assert "表：多群组测量等值性检验" in archive.read(apa_path).decode("utf-8")


def test_sem_model_wlsmv_execution() -> None:
    # 验证 WLSMV 分类变量修正路径
    dataset, measurement = _model_dataset()
    model = _sem_spec(
        dataset, measurement, estimator="WLSMV", group_variable=None, invariance=False
    )

    # 冻结模型
    freeze_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert freeze_response.status_code == 200, freeze_response.text
    frozen = freeze_response.json()

    # 运行 WLSMV 分析
    analysis_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen['version']}/analysis"
    )
    state = _await_analysis(analysis_response)
    result = state["result"]

    assert result["run"]["template"] == "sem"
    sem_res = result["semResult"]
    # 对于 DWLS/WLSMV，我们检查是否得到了 Robust 拟合指数
    assert sem_res["fitIndices"]["robustCfi"] is not None
    assert sem_res["fitIndices"]["robustChiSquare"] is not None
    assert "ordinal" in sem_res["numericReferenceMatrix"]
    _assert_sem_numeric_reference(sem_res, "WLSMV")


def test_sem_model_mlr_matches_locked_numeric_reference() -> None:
    dataset, measurement = _model_dataset()
    model = _sem_spec(
        dataset, measurement, estimator="MLR", group_variable=None, invariance=False
    )
    model["modelId"] = "sem_mlr_numeric_reference"
    frozen = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model, "override_reason": "锁定 MLR 数值参考矩阵。"},
    )
    assert frozen.status_code == 200, frozen.text
    result = _await_analysis(
        client.post(
            f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{frozen.json()['version']}/analysis"
        )
    )["result"]
    assert result["provenance"]["estimator"] == "MLR"
    assert result["semResult"]["fitIndices"]["robustChiSquare"] is not None
    _assert_sem_numeric_reference(result["semResult"], "MLR")


def test_sem_ml_fiml_retains_partially_observed_cases_and_reports_missingness() -> None:
    dataset, measurement = _model_dataset(with_missing=True)
    model = _sem_spec(dataset, measurement, estimator="ML", group_variable=None, invariance=False)
    model["modelId"] = "sem_fiml_test_model"
    model["estimation"]["missing"] = "fiml"

    freeze_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model, "override_reason": "测试 FIML 缺失数据处理。"},
    )
    assert freeze_response.status_code == 200, freeze_response.text

    state = _await_analysis(
        client.post(
            f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{freeze_response.json()['version']}/analysis"
        )
    )
    result = state["result"]

    assert result["sampleFlow"]["missingMethod"] == "fiml"
    assert result["sampleFlow"]["original"] == 300
    assert result["sampleFlow"]["included"] == 300
    assert result["sampleFlow"]["excluded"] == 0
    assert sum(result["sampleFlow"]["variableMissingCounts"].values()) > 0
    assert len(result["sampleFlow"]["missingPatterns"]) >= 2
    assert result["semResult"]["numericReferenceMatrix"]["execution"]["executedMissing"] == "fiml"
    _assert_sem_numeric_reference(result["semResult"], "FIML", executed_estimator="ML")


def test_wlsmv_invariance_uses_thresholds_for_scalar_model() -> None:
    dataset, measurement = _model_dataset()
    model = _sem_spec(
        dataset, measurement, estimator="WLSMV", group_variable="group", invariance=True
    )
    model["modelId"] = "sem_wlsmv_invariance_test_model"
    item_ids = {variable["originalName"]: variable["id"] for variable in dataset["variables"]}
    ordinal_item_ids = [item_ids[name] for name in ("x1", "x2", "m1", "m2", "y1", "y2")]
    # Keep this test focused on ordinal measurement invariance. The general
    # SEM fixture has three two-indicator factors plus multiple structural paths, which
    # becomes near-underidentified after grouping and tests optimizer churn
    # rather than the WLSMV threshold constraint contract.
    model["nodes"] = [
        next(node for node in model["nodes"] if node["id"] == "latent_f1"),
        next(node for node in model["nodes"] if node["id"] == "latent_f2"),
        next(node for node in model["nodes"] if node["id"] == "group"),
    ]
    model["latents"] = [
        {
            "id": "latent_f1",
            "name": "Factor1",
            "indicators": ordinal_item_ids[:3],
        },
        {
            "id": "latent_f2",
            "name": "Factor2",
            "indicators": ordinal_item_ids[3:],
        },
    ]
    model["edges"] = [model["edges"][0]]
    model["covariates"] = []
    model["estimation"]["multiGroup"] = {
        "compareStructuralPaths": False,
        "estimateLatentMeans": False,
        "partialInvarianceReleases": [
            {
                "stage": "scalar",
                "constraint": "intercept_or_threshold",
                "latentId": None,
                "indicatorId": ordinal_item_ids[0],
                "rationale": "预设释放该有序题项的组间阈值约束。",
            }
        ],
    }

    freeze_response = client.post(
        f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/freeze",
        json={"model_spec": model},
    )
    assert freeze_response.status_code == 200, freeze_response.text

    state = _await_analysis(
        client.post(
            f"/api/v1/datasets/{dataset['id']}/models/{model['modelId']}/versions/{freeze_response.json()['version']}/analysis"
        )
    )
    invariance = state["result"]["invarianceResult"]

    assert invariance["estimator"] == "WLSMV"
    assert sum(invariance["groupSizes"].values()) == 300
    scalar = next(
        model_result for model_result in invariance["models"] if model_result["model"] == "scalar"
    )
    assert scalar["constraints"] == ["loadings", "thresholds"]
    assert "intercepts" not in scalar["constraints"]
    assert any(
        parameter.startswith(f"{ordinal_item_ids[0]}|t")
        for parameter in scalar["releasedParameters"]
    )
    assert all(
        comparison["evaluationStatus"] in {"pass", "fail", "not_evaluable"}
        for comparison in invariance["comparisons"]
    )
