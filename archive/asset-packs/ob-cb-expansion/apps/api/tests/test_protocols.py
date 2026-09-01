from __future__ import annotations

from starlette.testclient import TestClient

from app.main import app
from app.protocol_contracts import (
    HypothesisInput,
    ResearchProgramSpec,
    StudyProtocolSpec,
)

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_program_creation_retrieval_and_duplicate_reject() -> None:
    # 1. Create program
    program_id = "program_test_123"
    program_data = {
        "id": program_id,
        "title": "测试研究计划",
        "theoreticalQuestion": "工作自主性如何通过敬业度影响绩效？",
        "targetJournal": "Journal of Applied Psychology",
        "owner": "李博士",
        "constructKeys": ["construct_autonomy", "construct_engagement", "construct_performance"],
    }
    response = client.post("/api/v1/programs", json=program_data)
    assert response.status_code == 201, response.text

    # 2. Retrieve program
    response = client.get(f"/api/v1/programs/{program_id}")
    assert response.status_code == 200
    program = ResearchProgramSpec.model_validate(response.json())
    assert program.id == program_id
    assert program.title == "测试研究计划"
    assert "construct_autonomy" in program.construct_keys

    # 3. Retrieve non-existent program
    response = client.get("/api/v1/programs/program_non_existent")
    assert response.status_code == 404


def test_protocol_draft_creation_retrieval_and_freeze() -> None:
    program_id = "program_test_freeze"
    client.post(
        "/api/v1/programs",
        json={
            "id": program_id,
            "title": "测试计划",
            "theoreticalQuestion": "测试问题",
        },
    )

    study_id = "study_survey_01"
    protocol_draft = {
        "studyId": study_id,
        "title": "第一项横截面问卷研究",
        "designType": "survey",
        "samplingPlan": {
            "population": "企业在职员工",
            "recruitment": "Credamo 平台招募",
            "inclusionCriteria": ["年龄在 18-60 岁之间", "全职工作满一年"],
            "exclusionCriteria": ["答题时长小于 120 秒", "注意力测试题答错"],
        },
        "plannedEstimands": [
            {
                "estimandId": "est_mediation",
                "outcomeVariableId": "var_performance",
                "predictorVariableIds": ["var_autonomy"],
                "covariateVariableIds": ["var_age", "var_gender"],
            }
        ],
    }

    # 1. Save draft
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/draft",
        json=protocol_draft,
    )
    assert response.status_code == 201, response.text

    # 2. Get draft
    response = client.get(f"/api/v1/programs/{program_id}/protocols/{study_id}/draft")
    assert response.status_code == 200
    draft = StudyProtocolSpec.model_validate(response.json())
    assert draft.study_id == study_id
    assert draft.sampling_plan.population == "企业在职员工"

    # 3. Freeze version
    version_id = "version_prereg_v1"
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/freeze?version_id={version_id}&preregistration_url=https://osf.io/prereg1",
    )
    assert response.status_code == 200
    res = response.json()
    assert res["status"] == "frozen"
    assert res["versionId"] == version_id
    assert "frozenHash" in res

    # 4. Get frozen version
    response = client.get(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/versions/{version_id}"
    )
    assert response.status_code == 200
    frozen = StudyProtocolSpec.model_validate(response.json())
    assert frozen.study_id == study_id
    assert frozen.preregistration_url == "https://osf.io/prereg1"

    # 5. Overwrite rejection
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/freeze?version_id={version_id}",
    )
    assert response.status_code == 409
    assert "已经存在，不可覆盖" in response.json()["detail"]


def test_same_study_id_is_isolated_between_programs() -> None:
    for program_id, title in (("program_isolation_a", "计划 A"), ("program_isolation_b", "计划 B")):
        response = client.post(
            "/api/v1/programs",
            json={
                "id": program_id,
                "title": title,
                "theoreticalQuestion": "同名 Study 隔离测试",
            },
        )
        assert response.status_code == 201, response.text
        response = client.post(
            f"/api/v1/programs/{program_id}/protocols/study_shared/draft",
            json={
                "studyId": "study_shared",
                "title": title,
                "designType": "survey",
            },
        )
        assert response.status_code == 201, response.text

    for program_id, title in (("program_isolation_a", "计划 A"), ("program_isolation_b", "计划 B")):
        response = client.get(f"/api/v1/programs/{program_id}/protocols/study_shared/draft")
        assert response.status_code == 200
        assert response.json()["title"] == title

    response = client.get("/api/v1/programs/program_isolation_a/studies")
    assert response.status_code == 200
    assert response.json()[0]["studyId"] == "study_shared"


def test_hypothesis_registration_and_list() -> None:
    program_id = "program_test_hyp"
    client.post(
        "/api/v1/programs",
        json={
            "id": program_id,
            "title": "测试计划",
            "theoreticalQuestion": "测试问题",
        },
    )
    study_id = "study_survey_02"

    hyp_data = {
        "id": "hyp_mediation_effect",
        "text": "工作自主性对绩效有正向中介效应",
        "directionality": "positive",
        "analysisRole": "primary",
        "isPreregistered": True,
        "status": "untested",
    }

    # 1. Add hypothesis
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/hypotheses",
        json=hyp_data,
    )
    assert response.status_code == 201, response.text

    # 2. List hypotheses
    response = client.get(f"/api/v1/programs/{program_id}/protocols/{study_id}/hypotheses")
    assert response.status_code == 200
    hyps = [HypothesisInput.model_validate(item) for item in response.json()]
    assert len(hyps) == 1
    assert hyps[0].id == "hyp_mediation_effect"
    assert hyps[0].analysis_role == "primary"


def test_deviation_checks() -> None:
    program_id = "program_test_deviation"
    client.post(
        "/api/v1/programs",
        json={
            "id": program_id,
            "title": "测试偏离计划",
            "theoreticalQuestion": "测试问题",
        },
    )
    study_id = "study_survey_03"

    protocol_draft = {
        "studyId": study_id,
        "title": "实验偏离对照",
        "designType": "survey",
        "samplingPlan": {
            "population": "全职员工",
        },
        "plannedEstimands": [
            {
                "estimandId": "est_mediation",
                "outcomeVariableId": "var_performance",
                "predictorVariableIds": ["var_autonomy"],
                "covariateVariableIds": ["var_age", "var_gender"],
            }
        ],
    }
    client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/draft",
        json=protocol_draft,
    )
    client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/freeze?version_id=v1",
    )

    # Case A: Matches perfectly
    analysis_spec_ok = {
        "outcomeVariableId": "var_performance",
        "predictorVariableIds": ["var_autonomy"],
        "controlVariableIds": ["var_age", "var_gender"],
    }
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/verify-deviation?version_id=v1",
        json=analysis_spec_ok,
    )
    assert response.status_code == 200
    assert len(response.json()) == 0

    # Case B: Outcome mismatch
    analysis_spec_outcome_wrong = {
        "outcomeVariableId": "var_engagement",
        "predictorVariableIds": ["var_autonomy"],
        "controlVariableIds": ["var_age", "var_gender"],
    }
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/verify-deviation?version_id=v1",
        json=analysis_spec_outcome_wrong,
    )
    assert response.status_code == 200
    deviations = response.json()
    assert len(deviations) == 1
    assert deviations[0]["deviationType"] == "outcome_mismatch"
    assert deviations[0]["fieldPath"] == "outcome_variable_id"

    # Case C: Covariate mismatch
    analysis_spec_covariates_wrong = {
        "outcomeVariableId": "var_performance",
        "predictorVariableIds": ["var_autonomy"],
        "controlVariableIds": ["var_age"],  # var_gender missing!
    }
    response = client.post(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/verify-deviation?version_id=v1",
        json=analysis_spec_covariates_wrong,
    )
    assert response.status_code == 200
    deviations = response.json()
    assert len(deviations) == 1
    assert deviations[0]["deviationType"] == "covariate_mismatch"

    response = client.get(
        f"/api/v1/programs/{program_id}/protocols/{study_id}/versions/v1/deviations"
    )
    assert response.status_code == 200
    assert {item["deviationType"] for item in response.json()} >= {
        "outcome_mismatch",
        "covariate_mismatch",
    }
