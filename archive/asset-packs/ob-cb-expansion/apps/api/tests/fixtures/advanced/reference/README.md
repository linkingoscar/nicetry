# Advanced statistical reference fixtures

These fixtures are validation references, not examples tuned to the current runner. Regenerate them with the project-locked R runtime:

```powershell
$env:R_LIBS_USER = (Resolve-Path ".runtime/R-library")
& ".runtime/R/bin/Rscript.exe" --vanilla "apps/api/tests/fixtures/advanced/reference/generate-goldens.R"
```

The generator fits each model directly with the cited reference package and never calls `run_advanced_analysis.R`.

| Slice | Public source | Deterministic derivation | Frozen comparison |
|---|---|---|---|
| Repeated measures / GG / EMM | `afex::obk.long`, O'Brien & Kaiser (1985), DOI `10.1037/0033-2909.97.2.316` | Average the five hourly observations within subject × treatment × phase | GG-corrected omnibus values, Mauchly/GG epsilon, EMM and pairwise 95% CI |
| Balanced factorial ANOVA | R `datasets::ToothGrowth` | Treat dose as a three-level factor; deterministic row subject ID | Type III 2×3 omnibus, cell EMM/CI and Holm pairwise contrasts |
| ANCOVA | `carData::Moore`, Moore & Krupat (1971) | Grand-mean center fscore | Type III ANCOVA, adjusted EMM/CI and Holm contrasts |
| Gaussian MLM | `lme4::sleepstudy`, Belenky et al. (2003) | Original data unchanged; extra scaled columns are failure-only | Fixed effects, Satterthwaite df, variance components, likelihood, ICC and R² |
| Unbalanced centered MLM | Deterministic derivative of `lme4::sleepstudy` | Remove 0–3 late days by subject; split Days into cluster mean and within deviation | Centering identities, fixed effects and likelihood; unequal cluster sizes |
| Longitudinal FIML | `lavaan::Demo.growth` | Monotone MAR attrition selected only from earlier observed waves | FIML parameter/CI, fit indices, retained N, per-wave attrition and missing patterns |
| Longitudinal FIML re-entry | `lavaan::Demo.growth` | Non-monotone MAR with disjoint T3-only and T4-only missing sets | FIML parameter/CI, retained N, attrition, re-entry and pattern count |

Each golden JSON records the data SHA-256, exact package versions, reference call, fields and tolerances. A package upgrade changes a golden only after the independent reference script and the application runner have both been reviewed; test tolerances must not be widened to accept drift.
