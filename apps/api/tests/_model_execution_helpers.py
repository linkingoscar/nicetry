from __future__ import annotations

import numpy as np
import pandas as pd

from app.settings import get_settings


def _process_percentile(values: np.ndarray, probability: float) -> float:
    """Match the type-6 quantiles used by PROCESS 5.0 for probe values."""
    return float(np.quantile(values, probability, method="weibull"))


def _moderated_mediation_median_reference(measurement: dict, template: str) -> float:
    settings = get_settings()
    data = pd.read_parquet(settings.state_root / measurement["derivedDataset"]["storage"])
    x = data["scale_x"].to_numpy(dtype=float)
    m = data["scale_m"].to_numpy(dtype=float)
    y = data["scale_y"].to_numpy(dtype=float)
    w = data["scale_w"].to_numpy(dtype=float)
    age = data["age"].to_numpy(dtype=float)
    x_centered = x - x.mean()
    w_centered = w - w.mean()
    w_median = _process_percentile(w, 0.50) - w.mean()
    if template == "model_7":
        m_design = np.column_stack(
            [np.ones(len(x)), x_centered, w_centered, x_centered * w_centered, age]
        )
        y_design = np.column_stack([np.ones(len(x)), x_centered, m, age])
        m_beta = np.linalg.lstsq(m_design, m, rcond=None)[0]
        y_beta = np.linalg.lstsq(y_design, y, rcond=None)[0]
        reference = (m_beta[1] + m_beta[3] * w_median) * y_beta[2]
    elif template == "model_8":
        m_design = np.column_stack(
            [np.ones(len(x)), x_centered, w_centered, x_centered * w_centered, age]
        )
        y_design = np.column_stack(
            [np.ones(len(x)), x_centered, m, w_centered, x_centered * w_centered, age]
        )
        m_beta = np.linalg.lstsq(m_design, m, rcond=None)[0]
        y_beta = np.linalg.lstsq(y_design, y, rcond=None)[0]
        reference = (m_beta[1] + m_beta[3] * w_median) * y_beta[2]
    elif template == "model_15":
        m_design = np.column_stack([np.ones(len(x)), x_centered, age])
        y_design = np.column_stack(
            [
                np.ones(len(x)),
                x_centered,
                m,
                w_centered,
                m * w_centered,
                x_centered * w_centered,
                age,
            ]
        )
        m_beta = np.linalg.lstsq(m_design, m, rcond=None)[0]
        y_beta = np.linalg.lstsq(y_design, y, rcond=None)[0]
        reference = m_beta[1] * (y_beta[2] + y_beta[4] * w_median)
    else:
        m_design = np.column_stack([np.ones(len(x)), x_centered, age])
        y_design = np.column_stack(
            [np.ones(len(x)), x_centered, m, w_centered, m * w_centered, age]
        )
        m_beta = np.linalg.lstsq(m_design, m, rcond=None)[0]
        y_beta = np.linalg.lstsq(y_design, y, rcond=None)[0]
        reference = m_beta[1] * (y_beta[2] + y_beta[4] * w_median)
    return reference
