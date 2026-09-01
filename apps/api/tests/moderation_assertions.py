from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


def assert_unified_moderation(
    result: dict,
    data: pd.DataFrame,
    beta: np.ndarray,
    covariance: np.ndarray,
) -> None:
    moderator_mean = float(data["scale_w"].mean())
    slope_covariance = covariance[np.ix_([1, 3], [1, 3])]
    for probe in result["probes"]:
        model_w = probe["moderatorValue"] - moderator_mean
        gradient = np.asarray([1.0, model_w])
        expected_effect = beta[1] + beta[3] * model_w
        expected_se = np.sqrt(gradient @ slope_covariance @ gradient)
        assert probe["effect"] == pytest.approx(expected_effect, abs=1e-8)
        assert probe["standardError"] == pytest.approx(expected_se, abs=1e-8)
        assert probe["statistic"] == pytest.approx(
            expected_effect / expected_se, abs=1e-8
        )
        assert probe["confidenceInterval"]["method"] == "hc3_t"

    assert len(result["johnsonNeymanResults"]) == 1
    jn = result["johnsonNeymanResults"][0]["result"]
    assert len(jn["grid"]) == 101
    assert jn["method"] == "hc3_t"
    critical = jn["criticalValue"]
    for row in (jn["grid"][0], jn["grid"][50], jn["grid"][-1]):
        model_w = row["moderatorValue"] - moderator_mean
        expected_effect = beta[1] + beta[3] * model_w
        gradient = np.asarray([1.0, model_w])
        expected_se = np.sqrt(gradient @ slope_covariance @ gradient)
        assert row["effect"] == pytest.approx(expected_effect, abs=1e-8)
        assert row["standardError"] == pytest.approx(expected_se, abs=1e-8)
        assert row["lower"] == pytest.approx(
            expected_effect - critical * expected_se, abs=1e-8
        )
        assert row["upper"] == pytest.approx(
            expected_effect + critical * expected_se, abs=1e-8
        )
        assert row["significant"] is (row["lower"] > 0 or row["upper"] < 0)
