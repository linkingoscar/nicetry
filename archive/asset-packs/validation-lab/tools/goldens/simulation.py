"""Monte Carlo Parameter Recovery Simulation Engine (Specification 28, Section 16.4 & 24).

Generates synthetic datasets from structured Data Generating Processes (DGPs),
executes statistical fits across N replications (e.g. 500-2000), and evaluates:
- Bias: (1/N_conv) * sum(est - true) on converged replications
- RMSE: sqrt((1/N_conv) * sum((est - true)^2))
- Coverage Rate: proportion of 95% CIs containing true parameter (denominator N_total, target 92.5% - 97.5%)
- Convergence Failure / Non-identifiable rate
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDENS_DIR = PROJECT_ROOT / "tests" / "goldens"


def generate_dgp_data(
    dgp_type: str,
    n_obs: int = 200,
    seed: int = 42,
    true_params: Optional[Dict[str, float]] = None,
) -> Tuple[np.ndarray, Dict[str, float]]:
    """Generates synthetic dataset and true parameters for a given DGP."""
    rng = np.random.default_rng(seed)

    if true_params is None:
        true_params = {}

    if dgp_type == "regression":
        beta0 = true_params.get("beta0", 2.5)
        beta1 = true_params.get("beta1", 1.8)
        sigma = true_params.get("sigma", 1.0)

        x = rng.normal(0, 1, size=(n_obs, 1))
        epsilon = rng.normal(0, sigma, size=(n_obs, 1))
        y = beta0 + beta1 * x[:, 0:1] + epsilon

        data = np.hstack([x, y])
        params = {"beta0": beta0, "beta1": beta1, "sigma": sigma}
        return data, params

    elif dgp_type == "t_test_two_sample":
        mu0 = true_params.get("mu0", 10.0)
        mean_diff = true_params.get("mean_diff", 1.5)
        sigma = true_params.get("sigma", 1.2)

        g0 = rng.normal(mu0, sigma, size=(n_obs // 2, 1))
        g1 = rng.normal(mu0 + mean_diff, sigma, size=(n_obs // 2, 1))
        group0 = np.hstack([np.zeros((n_obs // 2, 1)), g0])
        group1 = np.hstack([np.ones((n_obs // 2, 1)), g1])

        data = np.vstack([group0, group1])
        params = {"mean_diff": mean_diff, "sigma": sigma}
        return data, params

    elif dgp_type == "lmm_two_level":
        k_clusters = 20
        n_per_cluster = n_obs // k_clusters
        var_between = true_params.get("var_between", 1.0)
        var_within = true_params.get("var_within", 1.0)
        beta_fixed = true_params.get("beta_fixed", 1.2)

        u = rng.normal(0, np.sqrt(var_between), size=(k_clusters, 1))
        e = rng.normal(0, np.sqrt(var_within), size=(n_obs, 1))

        cluster_ids = np.repeat(np.arange(k_clusters), n_per_cluster).reshape(-1, 1)
        x = rng.normal(0, 1, size=(n_obs, 1))
        u_expanded = np.repeat(u, n_per_cluster).reshape(-1, 1)

        y = 2.0 + beta_fixed * x + u_expanded + e
        data = np.hstack([cluster_ids, x, y])
        params = {"beta_fixed": beta_fixed, "var_between": var_between, "var_within": var_within}
        return data, params

    elif dgp_type == "cfa_one_factor":
        lambda1 = true_params.get("lambda1", 0.8)
        lambda2 = true_params.get("lambda2", 0.7)
        lambda3 = true_params.get("lambda3", 0.75)

        eta = rng.normal(0, 1, size=(n_obs, 1))
        e1 = rng.normal(0, np.sqrt(1 - lambda1**2), size=(n_obs, 1))
        e2 = rng.normal(0, np.sqrt(1 - lambda2**2), size=(n_obs, 1))
        e3 = rng.normal(0, np.sqrt(1 - lambda3**2), size=(n_obs, 1))

        x1 = lambda1 * eta + e1
        x2 = lambda2 * eta + e2
        x3 = lambda3 * eta + e3

        data = np.hstack([x1, x2, x3])
        params = {"lambda1": lambda1, "lambda2": lambda2, "lambda3": lambda3}
        return data, params

    else:
        # Default OLS linear model
        beta0 = 1.0
        beta1 = 2.0
        x = rng.normal(0, 1, size=(n_obs, 1))
        y = beta0 + beta1 * x[:, 0:1] + rng.normal(0, 0.5, size=(n_obs, 1))
        data = np.hstack([x, y])
        return data, {"beta0": beta0, "beta1": beta1}


def fit_simulation_replication(data: np.ndarray, dgp_type: str) -> Dict[str, Any]:
    """Fit model on synthetic data and return point estimates and 95% CIs."""
    if dgp_type in ("regression", "default"):
        x = data[:, 0]
        y = data[:, 1]
        n = len(y)

        x_design = np.column_stack([np.ones(n), x])
        try:
            beta_hat, _, _, _ = np.linalg.lstsq(x_design, y, rcond=None)
            res = y - x_design @ beta_hat
            sigma_sq = np.sum(res**2) / (n - 2)
            cov_beta = sigma_sq * np.linalg.inv(x_design.T @ x_design)
            se_beta = np.sqrt(np.diag(cov_beta))

            b0_est = float(beta_hat[0])
            b1_est = float(beta_hat[1])
            sigma_est = float(np.sqrt(sigma_sq))

            sigma_se = sigma_est / np.sqrt(2.0 * n)
            b0_ci = (b0_est - 1.96 * se_beta[0], b0_est + 1.96 * se_beta[0])
            b1_ci = (b1_est - 1.96 * se_beta[1], b1_est + 1.96 * se_beta[1])
            sigma_ci = (sigma_est - 1.96 * sigma_se, sigma_est + 1.96 * sigma_se)

            return {
                "converged": True,
                "estimates": {"beta0": b0_est, "beta1": b1_est, "sigma": sigma_est},
                "confidence_intervals": {"beta0": b0_ci, "beta1": b1_ci, "sigma": sigma_ci},
            }
        except Exception:
            return {"converged": False, "estimates": {}, "confidence_intervals": {}}

    elif dgp_type == "t_test_two_sample":
        g0 = data[data[:, 0] == 0, 1]
        g1 = data[data[:, 0] == 1, 1]
        n0, n1 = len(g0), len(g1)

        m0, m1 = np.mean(g0), np.mean(g1)
        diff_est = float(m1 - m0)
        s0, s1 = np.var(g0, ddof=1), np.var(g1, ddof=1)
        sp_sq = ((n0 - 1) * s0 + (n1 - 1) * s1) / (n0 + n1 - 2)
        se_diff = float(np.sqrt(sp_sq * (1.0 / n0 + 1.0 / n1)))
        sigma_est = float(np.sqrt(sp_sq))

        df = n0 + n1 - 2
        se_sigma = sigma_est / np.sqrt(2.0 * df)
        diff_ci = (diff_est - 1.96 * se_diff, diff_est + 1.96 * se_diff)
        sigma_ci = (sigma_est - 1.96 * se_sigma, sigma_est + 1.96 * se_sigma)

        return {
            "converged": True,
            "estimates": {"mean_diff": diff_est, "sigma": sigma_est},
            "confidence_intervals": {"mean_diff": diff_ci, "sigma": sigma_ci},
        }

    elif dgp_type == "lmm_two_level":
        clusters = data[:, 0].astype(int)
        x = data[:, 1]
        y = data[:, 2]
        n = len(y)
        k_clusters = len(np.unique(clusters))
        j_per_cluster = n // k_clusters

        x_design = np.column_stack([np.ones(n), x])
        beta_hat, _, _, _ = np.linalg.lstsq(x_design, y, rcond=None)
        beta_fixed_est = float(beta_hat[1])
        res = y - x_design @ beta_hat
        se_beta = float(np.sqrt(np.sum(res**2) / (n - 2) / np.sum((x - np.mean(x)) ** 2)))
        beta_ci = (beta_fixed_est - 1.96 * se_beta, beta_fixed_est + 1.96 * se_beta)

        # ANOVA variance components on fixed effect residuals
        residuals = y - (beta_hat[0] + beta_hat[1] * x)
        cluster_means = [np.mean(residuals[clusters == c]) for c in range(k_clusters)]
        grand_mean = np.mean(residuals)
        ms_b = j_per_cluster * np.sum((cluster_means - grand_mean) ** 2) / (k_clusters - 1)
        ms_w = np.sum(
            [(residuals[clusters == c] - cluster_means[c]) ** 2 for c in range(k_clusters)]
        ) / (k_clusters * (j_per_cluster - 1))

        var_w_est = float(ms_w)
        var_b_est = float(max(0.001, (ms_b - ms_w) / j_per_cluster))

        se_vw = var_w_est * np.sqrt(2.0 / (k_clusters * (j_per_cluster - 1)))
        se_vb = (1.0 / j_per_cluster) * np.sqrt(
            2.0 * ms_b**2 / (k_clusters - 1) + 2.0 * ms_w**2 / (k_clusters * (j_per_cluster - 1))
        )

        vw_ci = (var_w_est - 1.96 * se_vw, var_w_est + 1.96 * se_vw)
        vb_ci = (var_b_est - 1.96 * se_vb, var_b_est + 1.96 * se_vb)

        return {
            "converged": True,
            "estimates": {
                "beta_fixed": beta_fixed_est,
                "var_between": var_b_est,
                "var_within": var_w_est,
            },
            "confidence_intervals": {
                "beta_fixed": beta_ci,
                "var_between": vb_ci,
                "var_within": vw_ci,
            },
        }

    elif dgp_type == "cfa_one_factor":
        cov_m = np.cov(data, rowvar=False)
        l1_est = float(np.sqrt(abs(cov_m[0, 1] * cov_m[0, 2] / (cov_m[1, 2] + 1e-8))))
        l2_est = float(np.sqrt(abs(cov_m[0, 1] * cov_m[1, 2] / (cov_m[0, 2] + 1e-8))))
        l3_est = float(np.sqrt(abs(cov_m[0, 2] * cov_m[1, 2] / (cov_m[0, 1] + 1e-8))))

        return {
            "converged": True,
            "estimates": {"lambda1": l1_est, "lambda2": l2_est, "lambda3": l3_est},
            "confidence_intervals": {
                "lambda1": (l1_est - 0.15, l1_est + 0.15),
                "lambda2": (l2_est - 0.15, l2_est + 0.15),
                "lambda3": (l3_est - 0.15, l3_est + 0.15),
            },
        }

    return {"converged": False, "estimates": {}, "confidence_intervals": {}}


import hashlib


def derive_deterministic_subseed(
    schema_version: str,
    capability_id: str,
    scenario_id: str,
    master_seed: int,
    replication_index: int,
) -> int:
    """Derives deterministic sub-seed using Spec 32 SIM-01 stable hash formula."""
    token = f"{schema_version}:{capability_id}:{scenario_id}:{master_seed}:{replication_index}"
    hash_bytes = hashlib.sha256(token.encode("utf-8")).digest()
    # Map first 4 bytes to 32-bit unsigned int
    return int.from_bytes(hash_bytes[:4], byteorder="big")


def run_parameter_recovery_simulation(
    dgp_type: str = "regression",
    replicates: int = 500,
    master_seed: int = 12345,
    n_obs: int = 200,
    capability_id: str = "simulation.parameter_recovery.v1",
    scenario_id: str = "default_scenario",
) -> Dict[str, Any]:
    """Runs N parameter recovery replications and computes summary statistics per Spec 28 and Spec 32."""
    _, true_params = generate_dgp_data(dgp_type, n_obs=n_obs, seed=master_seed)

    replications_log: List[Dict[str, Any]] = []

    for rep in range(replicates):
        sub_seed = derive_deterministic_subseed("0.1.0", capability_id, scenario_id, master_seed, rep)
        data, _ = generate_dgp_data(dgp_type, n_obs=n_obs, seed=sub_seed, true_params=true_params)
        fit_res = fit_simulation_replication(data, dgp_type)

        replications_log.append(
            {
                "replication": rep,
                "seed": sub_seed,
                "converged": fit_res.get("converged", False),
                "estimates": fit_res.get("estimates", {}),
                "confidence_intervals": fit_res.get("confidence_intervals", {}),
            }
        )

    param_names = list(true_params.keys())
    metrics_summary: Dict[str, Dict[str, float]] = {}

    total_n = float(replicates)
    converged_count = sum(1 for r in replications_log if r["converged"])
    convergence_rate = converged_count / total_n

    for p_name in param_names:
        true_val = true_params[p_name]

        converged_estimates: List[float] = []
        covered_count = 0

        for rep_res in replications_log:
            if rep_res["converged"] and p_name in rep_res["estimates"]:
                est_val = rep_res["estimates"][p_name]
                converged_estimates.append(est_val)
                ci = rep_res["confidence_intervals"].get(p_name)
                if ci and ci[0] <= true_val <= ci[1]:
                    covered_count += 1

        if converged_estimates:
            estimates_arr = np.array(converged_estimates)
            mean_est = float(np.mean(estimates_arr))
            bias = float(np.mean(estimates_arr - true_val))
            rmse = float(np.sqrt(np.mean((estimates_arr - true_val) ** 2)))
        else:
            mean_est = 0.0
            bias = 0.0
            rmse = 0.0

        coverage = covered_count / total_n

        metrics_summary[p_name] = {
            "trueValue": true_val,
            "meanEstimate": mean_est,
            "bias": bias,
            "rmse": rmse,
            "coverageRate": coverage,
            "coverageSatisfied": bool(0.925 <= coverage <= 0.975),
        }

    report = {
        "dgpType": dgp_type,
        "totalReplications": replicates,
        "convergenceRate": convergence_rate,
        "trueParameters": true_params,
        "parameterMetrics": metrics_summary,
        "overallPassed": bool(
            convergence_rate >= 0.95
            and all(m["coverageSatisfied"] for m in metrics_summary.values())
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Monte Carlo Parameter Recovery Engine")
    parser.add_argument(
        "--dgp",
        type=str,
        default="regression",
        help="DGP type (regression, t_test_two_sample, lmm_two_level, cfa_one_factor)",
    )
    parser.add_argument("--replicates", type=int, default=100, help="Number of replications")
    parser.add_argument("--seed", type=int, default=12345, help="Master RNG seed")
    parser.add_argument("--out", type=str, help="Output JSON report file path")
    args = parser.parse_args()

    print(f"Running Monte Carlo Parameter Recovery ({args.replicates} reps, DGP: {args.dgp})...")
    report = run_parameter_recovery_simulation(
        dgp_type=args.dgp,
        replicates=args.replicates,
        master_seed=args.seed,
    )

    print(
        f"\nParameter Recovery Summary (Convergence Rate: {report['convergenceRate'] * 100:.1f}%):"
    )
    for p_name, metrics in report["parameterMetrics"].items():
        cov_str = "[PASS]" if metrics["coverageSatisfied"] else "[FAIL]"
        print(
            f"  {cov_str} Parameter '{p_name}': True={metrics['trueValue']:.4f}, MeanEst={metrics['meanEstimate']:.4f}, Bias={metrics['bias']:.6f}, RMSE={metrics['rmse']:.6f}, Coverage={metrics['coverageRate'] * 100:.1f}%"
        )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\nReport saved to {out_path}")

    return 0 if report["overallPassed"] else 1


if __name__ == "__main__":
    sys.exit(main())
