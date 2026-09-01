import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.goldens.normalization import (  # type: ignore[reportMissingImports] # noqa: E402
    normalize_factor_loadings,
    normalize_pair_order,
    normalize_result_bundle,
    normalize_term_name,
)


def test_normalize_term_name() -> None:
    """INFRA-04: R/Python term names map to standard labels."""
    assert normalize_term_name("(Intercept)") == "intercept"
    assert normalize_term_name("Intercept") == "intercept"
    assert normalize_term_name("x1") == "x1"


def test_normalize_pair_order() -> None:
    """INFRA-04: Pair ordering is canonicalized with sign multiplier."""
    g1, g2, sign = normalize_pair_order("GroupB", "GroupA")
    assert (g1, g2) == ("GroupA", "GroupB")
    assert sign == -1

    g1_b, g2_b, sign_b = normalize_pair_order("GroupA", "GroupB")
    assert (g1_b, g2_b) == ("GroupA", "GroupB")
    assert sign_b == 1


def test_normalize_factor_loadings() -> None:
    """INFRA-04: Factor loading sign flip aligns column max magnitude to positive."""
    loadings = [
        [-0.8, 0.5],
        [-0.7, 0.6],
        [0.2, -0.9],
    ]
    aligned = normalize_factor_loadings(loadings)
    # Column 0: max abs is -0.8 -> flipped to positive
    assert aligned[0][0] == 0.8
    assert aligned[1][0] == 0.7
    # Column 1: max abs is -0.9 -> flipped to positive
    assert aligned[2][1] == 0.9


def test_normalize_result_bundle() -> None:
    """INFRA-04: Normalizes bundle estimates term labels."""
    bundle = {
        "estimates": [
            {"id": "b0", "label": "(Intercept)", "estimate": 2.5},
            {"id": "b1", "label": "x1", "estimate": 1.8},
        ]
    }
    norm = normalize_result_bundle(bundle)
    assert norm["estimates"][0]["label"] == "intercept"
