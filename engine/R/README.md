# R engine map

| File | Public role | Called by |
|---|---|---|
| `run_analysis.R` | Frozen PROCESS/path/SEM ModelSpec → ResultBundle | `app.services.r_engine` |
| `run_empirical_analysis.R` | Questionnaire methods plus latent longitudinal-panel, diary/ESM, multilevel MI and Monte Carlo planning evidence | `app.services.empirical_analysis` |
| `worker.R` | Resident task host for approved R entrypoints | `app.services.r_workers` |
| `lib/*.R` | Focused estimators, bootstrap, EFA/CFA/validity, runtime and resource helpers | Sourced by the public entrypoints |
| `r_sem_helpers.R` | lavaan fit, parameter and latent reliability helpers | `lib/sem_analysis.R` |

The three `run_*.R` files and `worker.R` are command entrypoints, not reusable libraries. New estimators should be placed in focused helper modules and sourced by an entrypoint. Do not move formulas into React or FastAPI routes. A branch that cannot pass the Python contract is not an implemented capability and should not remain as dormant executable code.

Remaining split targets:

- `run_analysis.R`: IO/progress, data preparation, equation compiler, estimators, bootstrap, SEM result assembly;
- `run_empirical_analysis.R`: descriptive/factorability, EFA, CFA, validity, group comparison, hierarchical regression, longitudinal panel and diary multilevel orchestration.
- The former general-purpose advanced runner is preserved in
  `archive/asset-packs/ob-cb-expansion/`. Focused longitudinal and two-level
  diary/ESM slices are active in `longitudinal_*.R` and `diary_*.R`, including
  measurement invariance, five-wave LCM-SR, longitudinal ULMC sensitivity,
  explicit ESM centering/time protocols, binary/count/zero-inflated/Hurdle
  GLMM, crossed random effects, observed-variable Bayesian DSEM with modern
  chain diagnostics and bounded plot evidence, multilevel MI and method-specific
  Monte Carlo power.

Split one statistical unit at a time and keep the existing NumPy/lavaan/boundary tests green after every extraction.
