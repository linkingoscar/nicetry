#!/usr/bin/env python3
"""Independent Analytical Two-Sample T-Test Power Reference Implementation (G1 Evidence)."""

import json
import math
from pathlib import Path

from scipy import stats


def main():
    case_dir = Path(__file__).resolve().parent.parent.parent
    spec_path = case_dir / "spec" / "analysis-spec.json"
    output_path = Path(__file__).resolve().parent / "normalized-output.json"

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    d = float(spec["effectSize"])
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
    elif not math.isfinite(d):
        result = _failure("INVALID_EFFECT_SIZE", "effectSize must be finite")
    else:
        df = n1 + n2 - 2
        n_eff = (n1 * n2) / (n1 + n2)
        ncp = d * math.sqrt(n_eff)

        t_crit = stats.t.ppf(1.0 - alpha / 2.0, df)
        power = float(1.0 - stats.nct.cdf(t_crit, df, ncp) + stats.nct.cdf(-t_crit, df, ncp))

        result = {
            "testType": "two_sample",
            "effectSize": d,
            "alpha": alpha,
            "n1": n1,
            "n2": n2,
            "df": df,
            "ncp": ncp,
            "power": power,
        }

    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("Power t-test primary reference output written")


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


if __name__ == "__main__":
    main()
