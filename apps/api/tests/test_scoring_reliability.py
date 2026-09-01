from __future__ import annotations

import pandas as pd
import pytest

from app.services.measurement import (
    cronbach_alpha,
    mcdonald_omega,
    spearman_brown_reliability,
)


def test_spearman_brown_two_item_scale() -> None:
    # Two perfectly correlated items
    df_perfect = pd.DataFrame({"item1": [1, 2, 3, 4, 5], "item2": [1, 2, 3, 4, 5]})
    sb_perfect = spearman_brown_reliability(df_perfect)
    assert sb_perfect is not None
    assert pytest.approx(sb_perfect, abs=1e-5) == 1.0

    # Moderate correlation: r = 0.5 -> SB = 2*0.5/(1+0.5) = 1/1.5 = 0.66667
    df_mod = pd.DataFrame({"item1": [1, 2, 3, 4, 5], "item2": [2, 1, 4, 3, 5]})
    sb_mod = spearman_brown_reliability(df_mod)
    assert sb_mod is not None
    assert 0.5 < sb_mod < 1.0

    # Omega should return None for 2 items
    assert mcdonald_omega(df_perfect) is None


def test_spearman_brown_uses_standard_denominator_for_negative_correlation() -> None:
    negatively_correlated = pd.DataFrame(
        {"item1": [1, 2, 3, 4, 5], "item2": [5, 3, 4, 2, 1]}
    )
    correlation = negatively_correlated.corr().iloc[0, 1]
    expected = 2 * correlation / (1 + correlation)
    actual = spearman_brown_reliability(negatively_correlated)
    assert actual == pytest.approx(expected, abs=1e-12)


def test_cronbach_alpha_basic() -> None:
    df = pd.DataFrame(
        {
            "item1": [1, 2, 3, 4, 5],
            "item2": [1, 2, 3, 4, 5],
            "item3": [1, 2, 3, 4, 5],
        }
    )
    alpha = cronbach_alpha(df)
    assert alpha is not None
    assert pytest.approx(alpha, abs=1e-5) == 1.0
