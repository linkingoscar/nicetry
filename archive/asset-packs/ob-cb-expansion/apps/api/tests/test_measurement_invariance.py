from __future__ import annotations

from app.services.advanced_analysis import advanced_analysis_registry


def test_measurement_invariance_slice_registered() -> None:
    capabilities = advanced_analysis_registry.capabilities()
    longitudinal_cap = next(c for c in capabilities if c["family"] == "longitudinal_model")
    invariance_slice = next(
        s
        for s in longitudinal_cap["slices"]
        if s["id"] == "longitudinal_model.longitudinal_invariance"
    )
    assert invariance_slice["executionAvailable"] is True
    assert invariance_slice["status"] == "experimental"
