from __future__ import annotations

import pandas as pd

from app.services.model_encoding import encode_node_series, predictor_columns


def test_age_is_mean_centered_before_model_estimation() -> None:
    encoded, errors = encode_node_series(
        {
            "id": "node_age",
            "label": "年龄",
            "dataType": "continuous",
            "encoding": {"method": "mean_center"},
        },
        pd.Series([20, 30, 40]),
    )
    assert errors == []
    assert encoded.tolist() == [-10.0, 0.0, 10.0]


def test_education_respects_declared_ordinal_order() -> None:
    encoded, errors = encode_node_series(
        {
            "id": "node_education",
            "label": "教育程度",
            "dataType": "ordinal",
            "encoding": {"method": "ordinal_score", "levels": ["高中", "本科", "硕士"]},
        },
        pd.Series(["硕士", "高中", "本科"]),
    )
    assert errors == []
    assert encoded.tolist() == [3.0, 1.0, 2.0]


def test_occupation_treatment_encoding_creates_k_minus_one_columns() -> None:
    encoded, errors = encode_node_series(
        {
            "id": "node_job",
            "label": "职业",
            "dataType": "nominal",
            "encoding": {
                "method": "treatment",
                "referenceLevel": "教师",
                "levels": ["教师", "企业", "公务员"],
            },
        },
        pd.Series(["教师", "企业", "公务员", "教师"]),
    )
    assert errors == []
    columns = predictor_columns(encoded)
    assert len(columns) == 2
    assert [column.tolist() for column in columns] == [[0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 1.0, 0.0]]
