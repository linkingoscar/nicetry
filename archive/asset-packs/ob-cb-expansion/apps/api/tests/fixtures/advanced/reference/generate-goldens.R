args <- commandArgs(trailingOnly = FALSE)
file_arg <- sub("^--file=", "", args[grepl("^--file=", args)])
reference_dir <- dirname(normalizePath(file_arg, winslash = "/", mustWork = TRUE))
advanced_dir <- dirname(reference_dir)
golden_dir <- file.path(advanced_dir, "goldens")
dir.create(golden_dir, recursive = TRUE, showWarnings = FALSE)

suppressPackageStartupMessages({
  library(afex)
  library(digest)
  library(emmeans)
  library(jsonlite)
  library(lavaan)
  library(lme4)
  library(lmerTest)
  library(performance)
})

write_fixture <- function(value, name) {
  path <- file.path(reference_dir, name)
  write.csv(value, path, row.names = FALSE, na = "", fileEncoding = "UTF-8")
  path
}

sha256 <- function(path) digest(path, algo = "sha256", file = TRUE, serialize = FALSE)
versions <- function(packages) as.list(vapply(packages, function(package) as.character(packageVersion(package)), character(1)))
rows <- function(value) {
  if (is.null(value) || NROW(value) == 0L) return(list())
  value <- as.data.frame(value)
  lapply(seq_len(nrow(value)), function(index) {
    result <- lapply(value, function(column) column[[index]])
    names(result) <- names(value)
    result
  })
}
write_golden <- function(value, name) {
  write_json(value, file.path(golden_dir, name), auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = NA)
}

# O'Brien & Kaiser (1985), distributed as afex::obk.long. The current supported
# slice has one within factor, so hour is deterministically averaged within
# subject x treatment x phase before the model is fitted.
data("obk.long", package = "afex")
obrien <- aggregate(value ~ id + treatment + phase, obk.long, mean)
obrien_path <- write_fixture(obrien, "obrien-kaiser-phase.csv")
obrien_reference <- read.csv(obrien_path, check.names = FALSE)
obrien_reference$treatment <- factor(obrien_reference$treatment)
obrien_reference$phase <- factor(obrien_reference$phase)
contrasts(obrien_reference$treatment) <- contr.sum(levels(obrien_reference$treatment))
obrien_fit <- afex::aov_car(
  value ~ treatment * phase + Error(id/phase),
  data = obrien_reference,
  type = 3L,
  factorize = FALSE
)
obrien_table <- as.data.frame(anova(obrien_fit, correction = "GG", es = "pes"))
obrien_table$term <- rownames(obrien_table)
obrien_grid <- emmeans::emmeans(obrien_fit, specs = c("treatment", "phase"))
obrien_summary <- summary(obrien_fit$Anova, multivariate = FALSE)
write_golden(list(
  provenance = list(
    dataset = "afex::obk.long (O'Brien & Kaiser, 1985)",
    source = "https://doi.org/10.1037/0033-2909.97.2.316",
    transformation = "Arithmetic mean across hour within id x treatment x phase; no stochastic operation",
    datasetSha256 = sha256(obrien_path),
    reference = "Independent afex::aov_car + emmeans::emmeans script",
    softwareVersions = versions(c("afex", "emmeans", "car")),
    tolerance = list(omnibus = 1e-8, epsilon = 1e-8, emm = 1e-8, contrast = 1e-8),
    comparisonFields = c("GG omnibus F/df/p", "Mauchly and GG epsilon", "EMM/SE/df/95% CI", "pairwise estimate/SE/df/95% CI/p")
  ),
  sampleFlow = list(original = nrow(obrien_reference), included = nrow(obrien_reference), excluded = 0L),
  familyResult = list(
    omnibusTests = rows(obrien_table),
    estimatedMarginalMeans = rows(as.data.frame(confint(obrien_grid, level = 0.95))),
    contrasts = rows(as.data.frame(summary(pairs(obrien_grid), infer = c(TRUE, TRUE), level = 0.95, adjust = "holm"))),
    sphericity = list(
      tests = rows(as.data.frame(obrien_summary$sphericity.tests)),
      corrections = rows(as.data.frame(obrien_summary$pval.adjustments)),
      selectedCorrection = "GG"
    )
  )
), "obrien-kaiser-phase.expected.json")
write_fixture(obrien[-1, , drop = FALSE], "obrien-kaiser-incomplete-wave.csv")
write_fixture(rbind(obrien, obrien[1, , drop = FALSE]), "obrien-kaiser-duplicate-cell.csv")

# R's public ToothGrowth data form a balanced 2 x 3 between-subject factorial
# design once numeric dose is explicitly treated as a factor.
data("ToothGrowth", package = "datasets")
tooth <- ToothGrowth
tooth$subject <- seq_len(nrow(tooth))
tooth_path <- write_fixture(tooth, "toothgrowth-factorial.csv")
tooth_reference <- read.csv(tooth_path, check.names = FALSE)
tooth_reference$supp <- factor(tooth_reference$supp)
tooth_reference$dose <- factor(tooth_reference$dose)
contrasts(tooth_reference$supp) <- contr.sum(levels(tooth_reference$supp))
contrasts(tooth_reference$dose) <- contr.sum(levels(tooth_reference$dose))
tooth_reference$.rp_subject <- seq_len(nrow(tooth_reference))
tooth_fit <- afex::aov_car(
  len ~ supp * dose + Error(.rp_subject),
  data = tooth_reference,
  type = 3L,
  factorize = FALSE
)
tooth_table <- as.data.frame(anova(tooth_fit, es = "pes"))
tooth_table$term <- rownames(tooth_table)
tooth_grid <- emmeans::emmeans(tooth_fit, specs = c("supp", "dose"))
write_golden(list(
  provenance = list(
    dataset = "datasets::ToothGrowth",
    source = "https://stat.ethz.ch/R-manual/R-devel/library/datasets/html/ToothGrowth.html",
    transformation = "dose is treated as a three-level factor; subject is deterministic row number",
    datasetSha256 = sha256(tooth_path),
    reference = "Independent afex::aov_car + emmeans::emmeans script",
    softwareVersions = versions(c("afex", "emmeans", "car")),
    tolerance = list(omnibus = 1e-8, emm = 1e-8, contrast = 1e-8),
    comparisonFields = c("Type III omnibus F/df/p", "EMM/SE/df/95% CI", "Holm pairwise estimate/SE/df/CI/p")
  ),
  familyResult = list(
    omnibusTests = rows(tooth_table),
    estimatedMarginalMeans = rows(as.data.frame(confint(tooth_grid, level = 0.95))),
    contrasts = rows(as.data.frame(summary(pairs(tooth_grid), infer = c(TRUE, TRUE), level = 0.95, adjust = "holm")))
  )
), "toothgrowth-factorial.expected.json")
write_fixture(
  tooth[!(tooth$supp == "OJ" & tooth$dose == 2), , drop = FALSE],
  "toothgrowth-empty-cell.csv"
)

# Moore & Krupat conformity data, distributed by carData. fscore is centered
# exactly as the runner specifies before the ANCOVA and EMM reference grid.
data("Moore", package = "carData")
moore <- Moore[, c("conformity", "fcategory", "fscore")]
moore$subject <- seq_len(nrow(moore))
moore$fscore_duplicate <- moore$fscore
moore_path <- write_fixture(moore, "moore-ancova.csv")
moore_reference <- read.csv(moore_path, check.names = FALSE)
moore_reference$fcategory <- factor(moore_reference$fcategory)
contrasts(moore_reference$fcategory) <- contr.sum(levels(moore_reference$fcategory))
moore_reference$fscore <- moore_reference$fscore - mean(moore_reference$fscore)
moore_reference$.rp_subject <- seq_len(nrow(moore_reference))
moore_fit <- afex::aov_car(
  conformity ~ fcategory + fscore + Error(.rp_subject),
  data = moore_reference,
  type = 3L,
  factorize = FALSE,
  observed = "fscore"
)
moore_table <- as.data.frame(anova(moore_fit, es = "pes"))
moore_table$term <- rownames(moore_table)
moore_grid <- emmeans::emmeans(moore_fit, specs = "fcategory")
write_golden(list(
  provenance = list(
    dataset = "carData::Moore (Moore & Krupat, 1971)",
    source = "https://rdrr.io/cran/carData/man/Moore.html",
    transformation = "fscore grand-mean centered; duplicate column is boundary-only and excluded from the gold fit",
    datasetSha256 = sha256(moore_path),
    reference = "Independent afex::aov_car + emmeans::emmeans script",
    softwareVersions = versions(c("afex", "emmeans", "car")),
    tolerance = list(omnibus = 1e-8, emm = 1e-8, contrast = 1e-8),
    comparisonFields = c("Type III ANCOVA F/df/p", "adjusted EMM/SE/df/95% CI", "Holm pairwise estimate/SE/df/CI/p")
  ),
  familyResult = list(
    omnibusTests = rows(moore_table),
    estimatedMarginalMeans = rows(as.data.frame(confint(moore_grid, level = 0.95))),
    contrasts = rows(as.data.frame(summary(pairs(moore_grid), infer = c(TRUE, TRUE), level = 0.95, adjust = "holm")))
  )
), "moore-ancova.expected.json")

# Belenky et al. (2003), distributed unchanged as lme4::sleepstudy. Extra
# scaled columns are deterministic numerical-stability boundary fixtures.
data("sleepstudy", package = "lme4")
sleep_reference <- sleepstudy
sleep_reference$DaysScaled100 <- sleep_reference$Days * 100
sleep_reference$DaysScaled1e4 <- sleep_reference$Days * 1e4
sleep_reference$DaysScaled1e7 <- sleep_reference$Days * 1e7
sleep_path <- write_fixture(sleep_reference, "sleepstudy.csv")
sleep_fit <- lmerTest::lmer(Reaction ~ Days + (Days | Subject), data = sleep_reference, REML = TRUE)
sleep_coefficients <- as.data.frame(coef(summary(sleep_fit, ddf = "Satterthwaite")))
sleep_coefficients$term <- rownames(sleep_coefficients)
sleep_kr_coefficients <- as.data.frame(coef(summary(sleep_fit, ddf = "Kenward-Roger")))
sleep_kr_coefficients$term <- rownames(sleep_kr_coefficients)
sleep_variances <- as.data.frame(VarCorr(sleep_fit))
sleep_icc <- performance::icc(sleep_fit)
sleep_r2 <- performance::r2(sleep_fit)
write_golden(list(
  provenance = list(
    dataset = "lme4::sleepstudy (Belenky et al., 2003)",
    source = "https://lme4.github.io/lme4/reference/sleepstudy.html",
    transformation = "Original three columns unchanged; scaled predictor columns are boundary-only and excluded from the gold fit",
    datasetSha256 = sha256(sleep_path),
    reference = "Independent lmerTest::lmer REML fit with Satterthwaite degrees of freedom",
    softwareVersions = versions(c("lme4", "lmerTest", "performance")),
    tolerance = list(fixedEffect = 1e-6, varianceComponent = 1e-6, fitIndex = 1e-6),
    comparisonFields = c("fixed effects/SE/df/t/p", "random variance/covariance", "AIC/BIC/logLik", "ICC", "marginal/conditional R2")
  ),
  sampleFlow = list(original = nrow(sleep_reference), included = nrow(sleep_reference), excluded = 0L, clusters = length(unique(sleep_reference$Subject))),
  familyResult = list(
    fixedEffects = rows(sleep_coefficients),
    kenwardRogerFixedEffects = rows(sleep_kr_coefficients),
    varianceComponents = rows(sleep_variances),
    fitIndices = list(AIC = AIC(sleep_fit), BIC = BIC(sleep_fit), logLik = as.numeric(logLik(sleep_fit)), r2 = as.list(sleep_r2)),
    icc = rows(as.data.frame(sleep_icc))
  )
), "sleepstudy-random-slope.expected.json")

# Deterministically remove late observations from alternating subjects so the
# public sleepstudy data have unequal cluster sizes and varying cluster means.
subject_levels <- levels(sleepstudy$Subject)
removal_count <- setNames((seq_along(subject_levels) - 1L) %% 4L, subject_levels)
keep_sleep <- vapply(seq_len(nrow(sleepstudy)), function(index) {
  subject <- as.character(sleepstudy$Subject[[index]])
  sleepstudy$Days[[index]] <= 9L - removal_count[[subject]]
}, logical(1))
sleep_centered <- sleepstudy[keep_sleep, , drop = FALSE]
sleep_centered_path <- write_fixture(sleep_centered, "sleepstudy-centered-unbalanced.csv")
sleep_centered_reference <- read.csv(sleep_centered_path, check.names = FALSE)
cluster_mean <- ave(sleep_centered_reference$Days, sleep_centered_reference$Subject, FUN = mean)
sleep_centered_reference$Days__between <- cluster_mean
sleep_centered_reference$Days <- sleep_centered_reference$Days - cluster_mean
sleep_centered_fit <- lmerTest::lmer(
  Reaction ~ Days + Days__between + (1 | Subject),
  data = sleep_centered_reference,
  REML = TRUE
)
sleep_centered_coefficients <- as.data.frame(coef(summary(sleep_centered_fit, ddf = "Satterthwaite")))
sleep_centered_coefficients$term <- rownames(sleep_centered_coefficients)
write_golden(list(
  provenance = list(
    dataset = "Deterministic unbalanced derivative of lme4::sleepstudy",
    source = "https://lme4.github.io/lme4/reference/sleepstudy.html",
    transformation = "Remove 0-3 latest days by subject index modulo four; group mean and within-cluster deviation calculated analytically",
    datasetSha256 = sha256(sleep_centered_path),
    reference = "Independent group-mean transformation + lmerTest::lmer REML fit",
    softwareVersions = versions(c("lme4", "lmerTest")),
    tolerance = list(centeredMean = 1e-12, fixedEffect = 1e-6, fitIndex = 1e-6),
    comparisonFields = c("within-cluster means equal zero", "between term equals original cluster mean", "fixed effects/SE/df/t/p", "AIC/BIC/logLik")
  ),
  clusterSizes = as.list(table(sleep_centered_reference$Subject)),
  familyResult = list(
    fixedEffects = rows(sleep_centered_coefficients),
    fitIndices = list(AIC = AIC(sleep_centered_fit), BIC = BIC(sleep_centered_fit), logLik = as.numeric(logLik(sleep_centered_fit)))
  )
), "sleepstudy-centered-unbalanced.expected.json")

# lavaan official Demo.growth data. Attrition is MAR by construction because
# later-wave missingness is selected only from values observed at earlier waves.
data("Demo.growth", package = "lavaan")
growth <- Demo.growth
names(growth)[match(c("t1", "t2", "t3", "t4"), names(growth))] <- c("y1", "y2", "y3", "y4")
growth$subject <- seq_len(nrow(growth))
drop_t3 <- order(growth$y1, decreasing = TRUE)[seq_len(40)]
eligible_t4 <- setdiff(seq_len(nrow(growth)), drop_t3)
drop_t4 <- eligible_t4[order(growth$y2[eligible_t4])[seq_len(60)]]
growth$y3[drop_t3] <- NA_real_
growth$y4[c(drop_t3, drop_t4)] <- NA_real_
growth <- growth[, c("subject", "y1", "y2", "y3", "y4")]
growth_path <- write_fixture(growth, "demo-growth-fiml-attrition.csv")
growth_syntax <- paste(c("y2 ~ y1", "y3 ~ y2", "y4 ~ y3"), collapse = "\n")
growth_fit <- lavaan::sem(growth_syntax, data = growth, estimator = "ML", missing = "fiml")
stopifnot(lavInspect(growth_fit, "converged"), isTRUE(lavInspect(growth_fit, "post.check")))
growth_parameters <- parameterEstimates(growth_fit, ci = TRUE, level = 0.95)
growth_parameters <- growth_parameters[growth_parameters$op == "~", , drop = FALSE]
growth_patterns <- lavInspect(growth_fit, "patterns")
write_golden(list(
  provenance = list(
    dataset = "lavaan::Demo.growth",
    source = "https://lavaan.ugent.be/tutorial/growth.html",
    transformation = "Monotone MAR attrition: 40 T3/T4 drops selected by observed y1; 60 additional T4 drops selected by observed y2",
    datasetSha256 = sha256(growth_path),
    reference = "Independent lavaan::sem observed autoregression with missing='fiml'",
    softwareVersions = versions(c("lavaan")),
    tolerance = list(parameter = 1e-6, fitIndex = 1e-6),
    comparisonFields = c("autoregressive estimate/SE/z/p/95% CI", "fit indices", "FIML ntotal", "per-wave attrition", "missing patterns")
  ),
  sampleFlow = list(original = nrow(growth), included = lavInspect(growth_fit, "ntotal"), excluded = 0L),
  familyResult = list(
    parameters = rows(growth_parameters),
    fitIndices = as.list(fitMeasures(growth_fit, c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr", "aic", "bic"))),
    waveSampleFlow = list(
      list(wave = "T1", observed = sum(!is.na(growth$y1)), attritionFromPrevious = 0L),
      list(wave = "T2", observed = sum(!is.na(growth$y2)), attritionFromPrevious = 0L),
      list(wave = "T3", observed = sum(!is.na(growth$y3)), attritionFromPrevious = 40L),
      list(wave = "T4", observed = sum(!is.na(growth$y4)), attritionFromPrevious = 60L)
    ),
    missingPatternCount = nrow(growth_patterns)
  )
), "demo-growth-fiml.expected.json")

# Non-monotone MAR fixture: 30 cases are missing at T3 but re-enter at T4;
# another 40 observed at T3 attrit at T4. Selection uses only y1/y2.
growth_reentry <- Demo.growth
names(growth_reentry)[match(c("t1", "t2", "t3", "t4"), names(growth_reentry))] <- c("y1", "y2", "y3", "y4")
growth_reentry$subject <- seq_len(nrow(growth_reentry))
missing_t3 <- order(growth_reentry$y1, decreasing = TRUE)[seq_len(30)]
eligible_t4_drop <- setdiff(seq_len(nrow(growth_reentry)), missing_t3)
missing_t4 <- eligible_t4_drop[order(growth_reentry$y2[eligible_t4_drop])[seq_len(40)]]
growth_reentry$y3[missing_t3] <- NA_real_
growth_reentry$y4[missing_t4] <- NA_real_
growth_reentry <- growth_reentry[, c("subject", "y1", "y2", "y3", "y4")]
growth_reentry_path <- write_fixture(growth_reentry, "demo-growth-fiml-nonmonotone.csv")
growth_reentry_fit <- lavaan::sem(growth_syntax, data = growth_reentry, estimator = "ML", missing = "fiml")
stopifnot(lavInspect(growth_reentry_fit, "converged"), isTRUE(lavInspect(growth_reentry_fit, "post.check")))
growth_reentry_parameters <- parameterEstimates(growth_reentry_fit, ci = TRUE, level = 0.95)
growth_reentry_parameters <- growth_reentry_parameters[growth_reentry_parameters$op == "~", , drop = FALSE]
write_golden(list(
  provenance = list(
    dataset = "lavaan::Demo.growth",
    source = "https://lavaan.ugent.be/tutorial/growth.html",
    transformation = "Non-monotone MAR: 30 T3-only missing cases selected by y1 and 40 T4-only missing cases selected by y2",
    datasetSha256 = sha256(growth_reentry_path),
    reference = "Independent lavaan::sem observed autoregression with missing='fiml'",
    softwareVersions = versions(c("lavaan")),
    tolerance = list(parameter = 1e-6, fitIndex = 1e-6),
    comparisonFields = c("FIML parameter/CI", "ntotal=400", "T4 re-entry=30", "non-monotone missing patterns")
  ),
  familyResult = list(
    parameters = rows(growth_reentry_parameters),
    fitIndices = as.list(fitMeasures(growth_reentry_fit, c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr", "aic", "bic"))),
    waveObserved = c(400L, 400L, 370L, 360L),
    attritionFromPrevious = c(0L, 0L, 30L, 40L),
    reenteredFromPrevious = c(0L, 0L, 0L, 30L),
    missingPatternCount = nrow(lavInspect(growth_reentry_fit, "patterns"))
  )
), "demo-growth-fiml-nonmonotone.expected.json")

# Deterministic singular covariance fixture for the longitudinal failure path.
nonpd <- data.frame(
  subject = seq_len(30),
  y1 = seq_len(30),
  y2 = seq_len(30),
  y3 = seq_len(30) * 2,
  y4 = seq_len(30) * 3
)
write_fixture(nonpd, "longitudinal-non-positive-definite.csv")
