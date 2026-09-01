from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from starlette.testclient import TestClient

from app.main import app
from app.services.dataset_import import (
    DatasetImportError,
    _read_dataframe,
)
from app.services.dataset_merge import merge_datasets

client = TestClient(
    app,
    headers={"X-ResearchPath-Token": app.state.services.settings.session_token},
)


def test_xlsx_custom_sheet_selection(tmp_path) -> None:
    path = tmp_path / "custom-sheets.xlsx"
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        pd.DataFrame({"x": [10, 20]}).to_excel(writer, sheet_name="First", index=False)
        pd.DataFrame({"y": [100, 200]}).to_excel(writer, sheet_name="Second", index=False)

    # If selected_sheet is specified
    df, metadata, warnings = _read_dataframe(path, "xlsx", selected_sheet="Second")
    assert list(df.columns) == ["y"]
    assert df["y"].tolist() == [100, 200]
    assert metadata["sheet"] == "Second"

    # If selected_sheet does not exist
    with pytest.raises(DatasetImportError, match="不存在于该工作簿中"):
        _read_dataframe(path, "xlsx", selected_sheet="Third")


def test_qualtrics_csv_triple_headers(tmp_path) -> None:
    path = tmp_path / "qualtrics.csv"
    csv_content = (
        "ResponseId,Finished,Q1,Q2\n"
        "Response ID,Finished,How satisfied are you?,What is your age?\n"
        '{"ImportId":"ResponseId"},{"ImportId":"Finished"},{"ImportId":"QID1"},{"ImportId":"QID2"}\n'
        "R_1,1,5,25\n"
        "R_2,1,4,30\n"
    )
    path.write_text(csv_content, encoding="utf-8")

    df, metadata, warnings = _read_dataframe(path, "csv")
    assert df.shape == (2, 4)
    assert list(df.columns) == ["ResponseId", "Finished", "Q1", "Q2"]
    assert df["Q1"].tolist() == [5, 4]
    assert df["Q2"].tolist() == [25, 30]

    # Verify metadata labels matching row 1 (the second row)
    assert metadata["labels"]["Q1"] == "How satisfied are you?"
    assert metadata["labels"]["Q2"] == "What is your age?"
    assert any("Qualtrics" in w for w in warnings)


def test_pyreadstat_dta_and_por_import_mocked(tmp_path) -> None:
    # We mock pyreadstat.read_dta and pyreadstat.read_por
    mock_df = pd.DataFrame({"subject_id": [1, 2], "val": [10.5, 20.3]})
    mock_meta = MagicMock()
    mock_meta.column_names_to_labels = {"subject_id": "Subject Identifier", "val": "Value"}
    mock_meta.variable_value_labels = {}

    with (
        patch("pyreadstat.read_dta", return_value=(mock_df, mock_meta)) as mock_dta,
        patch("pyreadstat.read_por", return_value=(mock_df, mock_meta)) as mock_por,
    ):
        # Test DTA
        dta_path = tmp_path / "mock.dta"
        dta_path.touch()
        df_dta, meta_dta, warnings_dta = _read_dataframe(dta_path, "dta")
        assert df_dta.shape == (2, 2)
        assert meta_dta["labels"]["subject_id"] == "Subject Identifier"
        assert mock_dta.call_count > 0

        # Test POR
        por_path = tmp_path / "mock.por"
        por_path.touch()
        df_por, meta_por, warnings_por = _read_dataframe(por_path, "por")
        assert df_por.shape == (2, 2)
        assert meta_por["labels"]["val"] == "Value"
        assert mock_por.call_count > 0


def test_merge_datasets_algorithm() -> None:
    df1 = pd.DataFrame(
        {
            "userId": ["user1", "user2", "user3"],
            "wave": [1, 1, 1],
            "age": [20, 25, 30],
            "score": [80, 85, 90],
        }
    )
    df2 = pd.DataFrame(
        {
            "userId": ["user2", "user3", "user4"],
            "wave": [1, 1, 1],
            "satisfaction": [5, 4, 5],
            "score": [95, 90, 85],
        }
    )

    # Simple merge on userId (1-wave setup)
    merged, summary = merge_datasets(df1, df2, subject_key="userId")
    assert merged.shape == (
        4,
        7,
    )  # userId, wave, age, score, wave__target, satisfaction, score__target
    assert summary["matchedCount"] == 2  # user2, user3
    assert summary["primaryOnlyCount"] == 1  # user1
    assert summary["targetOnlyCount"] == 1  # user4
    assert summary["primaryDuplicates"] == 0
    assert summary["targetDuplicates"] == 0

    # Merge on userId + wave
    merged_wave, summary_wave = merge_datasets(df1, df2, subject_key="userId", wave_key="wave")
    assert merged_wave.shape == (4, 6)  # score__target but wave is merged
    assert summary_wave["matchedCount"] == 2

    # Duplicate warning test
    df_dup = pd.DataFrame({"userId": ["user1", "user1"], "val": [10, 20]})
    df_single = pd.DataFrame({"userId": ["user1"], "val2": [100]})
    _, summary_dup = merge_datasets(df_dup, df_single, subject_key="userId")
    assert summary_dup["primaryDuplicates"] == 2
    warnings_list = summary_dup["warnings"]
    assert isinstance(warnings_list, list)
    assert len(warnings_list) > 0


def test_merge_rejects_missing_keys_and_reports_many_to_many() -> None:
    primary = pd.DataFrame({"id": [1, 1], "wave": [1, 1], "x": [10, 20]})
    target = pd.DataFrame({"id": [1, 1], "wave": [1, 1], "y": [30, 40]})

    with pytest.raises(DatasetImportError, match="主数据集"):
        merge_datasets(primary.drop(columns="id"), target, subject_key="id")
    with pytest.raises(DatasetImportError, match="目标数据集"):
        merge_datasets(primary, target.drop(columns="id"), subject_key="id")
    with pytest.raises(DatasetImportError, match="主数据集"):
        merge_datasets(primary.drop(columns="wave"), target, subject_key="id", wave_key="wave")
    with pytest.raises(DatasetImportError, match="目标数据集"):
        merge_datasets(primary, target.drop(columns="wave"), subject_key="id", wave_key="wave")

    merged, summary = merge_datasets(primary, target, subject_key="id", wave_key="wave")
    assert len(merged) == 4
    assert summary["manyToManyConflictCount"] == 1
    assert summary["duplicateKeyDetails"] == [
        {
            "key": ["1", "1"],
            "primaryCount": 2,
            "targetCount": 2,
            "cardinality": "many_to_many",
        }
    ]


def test_api_datasets_import_and_merge_lifecycle(tmp_path) -> None:
    # 1. Create and import primary dataset
    primary_data = pd.DataFrame({"userId": [1, 2, 3], "wave": [1, 1, 1], "score_t1": [10, 20, 30]})
    primary_buf = BytesIO()
    primary_data.to_csv(primary_buf, index=False)
    primary_buf.seek(0)

    resp1 = client.post(
        "/api/v1/datasets/import",
        files={"file": ("t1.csv", primary_buf, "text/csv")},
    )
    assert resp1.status_code == 201
    primary_id = resp1.json()["id"]

    # 2. Create and import target dataset
    target_data = pd.DataFrame({"userId": [2, 3, 4], "wave": [1, 1, 1], "score_t2": [15, 25, 35]})
    target_buf = BytesIO()
    target_data.to_csv(target_buf, index=False)
    target_buf.seek(0)

    resp2 = client.post(
        "/api/v1/datasets/import",
        files={"file": ("t2.csv", target_buf, "text/csv")},
    )
    assert resp2.status_code == 201
    target_id = resp2.json()["id"]

    # 3. Request merge via API
    merge_req = {"target_dataset_id": target_id, "subject_key": "userId", "wave_key": "wave"}
    resp_merge = client.post(
        f"/api/v1/datasets/{primary_id}/merge",
        json=merge_req,
    )
    assert resp_merge.status_code == 201
    merge_data = resp_merge.json()
    assert "dataset" in merge_data
    assert "report" in merge_data

    merged_dataset = merge_data["dataset"]
    report = merge_data["report"]

    assert report["matchedCount"] == 2
    assert report["primaryOnlyCount"] == 1
    assert report["targetOnlyCount"] == 1
    assert merged_dataset["rowCount"] == 4
