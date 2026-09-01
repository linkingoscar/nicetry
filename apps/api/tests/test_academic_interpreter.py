from __future__ import annotations

from app.services.academic_interpreter import generate_interpretation_assets


def test_empirical_interpretation_does_not_invent_a_mediation_model() -> None:
    result = {
        "sample": {"rowCount": 120, "constructCount": 3},
        "descriptives": [],
        "factorability": {"kmo": 0.81, "bartlett": {"pValue": 0.0001}},
        "efa": {"method": "principal_axis", "factorCount": 3},
        "cfa": {"available": False, "reason": "not estimable"},
        "validity": {"constructs": []},
        "options": {"correlationMethod": "spearman"},
    }

    prose, _ = generate_interpretation_assets(result, {})

    assert "问卷实证证据摘要" in prose
    assert "spearman" in prose
    assert "Model 4" not in prose
    assert "间接效应" not in prose


def test_empirical_interpretation_marks_small_sample_cfa_as_exploratory() -> None:
    result = {
        "sample": {
            "rowCount": 24,
            "constructCount": 3,
            "measurementAdequacy": {
                "completeCases": 24,
                "casesPerParameter": 0.89,
            },
        },
        "descriptives": [],
        "factorability": {"kmo": 0.81, "bartlett": {"pValue": 0.0001}},
        "efa": {"method": "principal_axis", "factorCount": 3},
        "cfa": {
            "available": True,
            "validForConfirmatoryInterpretation": False,
            "cfi": 0.96,
            "tli": 0.95,
            "rmsea": 0.05,
            "srmr": 0.04,
        },
        "validity": {"constructs": []},
        "options": {"correlationMethod": "pearson"},
    }

    prose, _ = generate_interpretation_assets(result, {})

    assert "未达到平台的保守确认性解释护栏" in prose
    assert "不是通用样本量定理" in prose
    assert "仅宜作探索或流程演示" in prose


def test_moderated_mediation_distinguishes_conditionals_from_simple_slopes() -> None:
    result = {
        "run": {"template": "model_8"},
        "equations": [],
        "effects": [
            {
                "id": "effect_index",
                "type": "index",
                "estimate": 0.12,
                "confidenceInterval": {"lower": 0.03, "upper": 0.21},
            },
            {
                "id": "effect_conditional_mean",
                "type": "conditional",
                "label": "W at mean",
                "estimate": 0.20,
                "confidenceInterval": {"lower": 0.08, "upper": 0.32},
            },
        ],
        "probes": [{"label": "mean", "effect": 0.4}],
    }

    prose, _ = generate_interpretation_assets(result, {"estimation": {}})

    assert "条件间接效应" in prose
    assert "简单斜率属于被调节路径的条件效应，不是条件间接效应" in prose


def test_mediation_interpretation_reads_actual_bootstrap_replicates() -> None:
    result = {
        "run": {"template": "model_4"},
        "equations": [],
        "effects": [
            {
                "id": "effect_indirect",
                "type": "indirect",
                "estimate": 0.15,
                "confidenceInterval": {
                    "lower": 0.04,
                    "upper": 0.27,
                    "method": "bootstrap_percentile",
                    "replicates": 1234,
                },
            }
        ],
    }

    prose, _ = generate_interpretation_assets(result, {"estimation": {}})

    assert "1234 次" in prose
    assert "5000 次" not in prose


def test_serial_mediation_interpretation_reports_indirect_contrasts() -> None:
    result = {
        "run": {"template": "model_6"},
        "equations": [],
        "effects": [
            {
                "id": "effect_indirect_1",
                "type": "indirect",
                "label": "ind1",
                "estimate": 0.20,
                "confidenceInterval": {"lower": 0.08, "upper": 0.32},
            },
            {
                "id": "effect_contrast_ind1_ind2",
                "type": "contrast",
                "label": "ind1 - ind2",
                "estimate": 0.12,
                "confidenceInterval": {"lower": 0.03, "upper": 0.22},
            },
        ],
    }

    prose, _ = generate_interpretation_assets(result, {"estimation": {}})

    assert "Bootstrap 两两差异" in prose
    assert "ind1 - ind2" in prose
    assert "区间排除 0" in prose


def test_sem_interpretation_uses_sem_paths() -> None:
    result = {
        "run": {"template": "sem"},
        "semResult": {
            "fitIndices": {
                "chiSquare": 10.2,
                "df": 8,
                "pValue": 0.25,
                "cfi": 0.98,
                "tli": 0.97,
                "rmsea": 0.03,
                "srmr": 0.02,
            },
            "paths": [
                {
                    "from": "X",
                    "to": "Y",
                    "estimate": 0.4,
                    "standardError": 0.1,
                    "statistic": 4.0,
                    "pValue": 0.0001,
                    "stdAll": 0.35,
                    "ciLower": 0.236,
                    "ciUpper": 0.564,
                }
            ],
        },
        "provenance": {"confidenceLevel": 0.90},
    }

    prose, tables = generate_interpretation_assets(result, {"estimation": {"estimator": "ML"}})

    assert "共估计 1 条路径" in prose
    assert "X → Y" in tables
    assert "90% CI" in tables
    assert "[0.236, 0.564]" in tables
    assert "95% CI" not in tables
