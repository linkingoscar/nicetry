#!/usr/bin/env python3
"""Independent arbitrary-precision quadrature reference for two-sample t power."""

import json
import math
from pathlib import Path

import mpmath as mp


def _failure(reason_code, message):
    return {
        "failure": {
            "status": "failed",
            "reasonCode": reason_code,
            "message": message,
            "mustNotReturnEstimates": True,
            "mustNotFallback": True,
        }
    }


def _central_t_cdf(value, degrees):
    if value == 0:
        return mp.mpf("0.5")
    ratio = degrees / (degrees + value * value)
    tail = mp.betainc(degrees / 2, mp.mpf("0.5"), 0, ratio, regularized=True) / 2
    return 1 - tail if value > 0 else tail


def _central_t_quantile(probability, degrees):
    lower = mp.mpf("0")
    upper = mp.mpf("1")
    while _central_t_cdf(upper, degrees) < probability:
        upper *= 2
    for _ in range(180):
        midpoint = (lower + upper) / 2
        if _central_t_cdf(midpoint, degrees) < probability:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2


def _normal_cdf(value):
    return (1 + mp.erf(value / mp.sqrt(2))) / 2


def _noncentral_t_cdf(value, degrees, noncentrality):
    coefficient = 1 / (mp.power(2, degrees / 2) * mp.gamma(degrees / 2))

    def integrand(chi_square):
        density = coefficient * mp.power(chi_square, degrees / 2 - 1) * mp.exp(-chi_square / 2)
        conditional = _normal_cdf(value * mp.sqrt(chi_square / degrees) - noncentrality)
        return conditional * density

    return mp.quad(integrand, [0, degrees, mp.inf])


def main():
    mp.mp.dps = 60
    case_dir = Path(__file__).resolve().parent.parent.parent
    spec = json.loads((case_dir / "spec" / "analysis-spec.json").read_text(encoding="utf-8"))
    output_path = Path(__file__).resolve().parent / "normalized-output.json"
    effect = float(spec["effectSize"])
    alpha = float(spec["alpha"])
    n1 = int(spec["n1"])
    n2 = int(spec["n2"])

    if spec.get("testType") != "two_sample":
        result = _failure("UNSUPPORTED_TEST_TYPE", "Only independent two-sample t-test power is supported")
    elif spec.get("alternative") != "two_sided":
        result = _failure("UNSUPPORTED_ALTERNATIVE", "Only two-sided t-test power is supported")
    elif not 0.0 < alpha < 1.0:
        result = _failure("INVALID_ALPHA", "alpha must be finite and strictly between 0 and 1")
    elif n1 < 2 or n2 < 2:
        result = _failure("INVALID_SAMPLE_SIZE", "n1 and n2 must both be integers greater than or equal to 2")
    elif not math.isfinite(effect):
        result = _failure("INVALID_EFFECT_SIZE", "effectSize must be finite")
    else:
        degrees = n1 + n2 - 2
        noncentrality = mp.mpf(str(effect)) * mp.sqrt(mp.mpf(n1 * n2) / (n1 + n2))
        critical = _central_t_quantile(1 - mp.mpf(str(alpha)) / 2, degrees)
        power = _noncentral_t_cdf(-critical, degrees, noncentrality) + 1 - _noncentral_t_cdf(
            critical, degrees, noncentrality
        )
        result = {
            "testType": "two_sample",
            "effectSize": effect,
            "alpha": alpha,
            "n1": n1,
            "n2": n2,
            "df": degrees,
            "ncp": float(noncentrality),
            "power": float(power),
        }

    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Power t-test secondary reference output written")


if __name__ == "__main__":
    main()
