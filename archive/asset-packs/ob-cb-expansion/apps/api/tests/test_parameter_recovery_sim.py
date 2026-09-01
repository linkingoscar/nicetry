import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.goldens.simulation import (  # type: ignore[import-untyped] # noqa: E402
    derive_deterministic_subseed,
    run_parameter_recovery_simulation,
)


def test_deterministic_subseed_derivation() -> None:
    """SIM-01: Sub-seed derivation must be deterministic and independent of order."""
    seed1 = derive_deterministic_subseed("0.1.0", "power.regression", "normal", 12345, 0)
    seed2 = derive_deterministic_subseed("0.1.0", "power.regression", "normal", 12345, 0)
    seed3 = derive_deterministic_subseed("0.1.0", "power.regression", "normal", 12345, 1)

    assert seed1 == seed2
    assert seed1 != seed3


def test_regression_parameter_recovery() -> None:
    """SIM-02 & SIM-03: Verifies OLS linear regression parameter recovery (bias, RMSE, 95% coverage)."""
    report = run_parameter_recovery_simulation(
        dgp_type="regression",
        replicates=50,
        master_seed=42,
        n_obs=150,
    )

    assert report["dgpType"] == "regression"
    assert report["convergenceRate"] == 1.0
    assert "beta1" in report["parameterMetrics"]

    beta1_metrics = report["parameterMetrics"]["beta1"]
    assert abs(beta1_metrics["bias"]) < 0.15
    assert beta1_metrics["rmse"] < 0.3
    assert beta1_metrics["coverageRate"] > 0.85


def test_t_test_parameter_recovery() -> None:
    """SIM-02 & SIM-03: Verifies two-sample t-test mean difference parameter recovery."""
    report = run_parameter_recovery_simulation(
        dgp_type="t_test_two_sample",
        replicates=50,
        master_seed=101,
        n_obs=100,
    )

    assert report["convergenceRate"] == 1.0
    assert "mean_diff" in report["parameterMetrics"]
    md = report["parameterMetrics"]["mean_diff"]
    assert abs(md["bias"]) < 0.2
