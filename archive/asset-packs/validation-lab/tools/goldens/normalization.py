"""Cross-Engine Normalization Library (INFRA-04 per Spec 32, Section 8).

Provides deterministic term name mapping, factor sign/column alignment,
contrast pair ordering, and group label normalization across Python and R engines.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


TERM_MAPPING = {
    "(Intercept)": "intercept",
    "Intercept": "intercept",
    "sigma^2": "residual_variance",
    "Residual": "residual_variance",
}


def normalize_term_name(term: str) -> str:
    """Map software-specific term names to standard ResearchPath terms."""
    return TERM_MAPPING.get(term, term)


def normalize_pair_order(group1: str, group2: str) -> Tuple[str, str, int]:
    """Returns canonical sorted pair (A, B) and sign multiplier (+1 or -1)."""
    if group1 <= group2:
        return group1, group2, 1
    else:
        return group2, group1, -1


def normalize_factor_loadings(loadings: List[List[float]]) -> List[List[float]]:
    """Aligns factor signs so that the largest magnitude element in each factor column is positive."""
    if not loadings or not loadings[0]:
        return loadings

    import numpy as np

    matrix = np.array(loadings, dtype=float)
    n_rows, n_cols = matrix.shape

    for col in range(n_cols):
        max_idx = np.argmax(np.abs(matrix[:, col]))
        if matrix[max_idx, col] < 0:
            matrix[:, col] = -matrix[:, col]

    return matrix.tolist()


def normalize_result_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes result bundle inplace or returns normalized dictionary."""
    normalized = dict(bundle)

    # Normalize estimates
    if "estimates" in normalized and isinstance(normalized["estimates"], list):
        norm_estimates = []
        for item in normalized["estimates"]:
            if isinstance(item, dict) and "label" in item:
                item_copy = dict(item)
                item_copy["label"] = normalize_term_name(item_copy["label"])
                norm_estimates.append(item_copy)
            else:
                norm_estimates.append(item)
        normalized["estimates"] = norm_estimates

    return normalized
