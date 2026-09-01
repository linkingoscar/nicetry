# Public-data diary/ESM LMM validation: fit_diary_multilevel (the empirical
# workspace's two-level LMM path) vs the canonical Bates sleepstudy fit.
#
# Oracle: output/validation-datasets/oracle/mlm/sleepstudy_lmer.json (lme4 on
# the identical data). The diary spec uses raw (uncentered) Days,
# contemporaneous effect, independent residuals and a random slope, which is
# exactly the Bates model; tolerances are tight because both sides run lme4.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
public_data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)

source_engine <- function(relative_path) {
  # Same convention as the engine entry points: no explicit encoding
  # conversion, native R reading (UTF-8 files under the harness locale).
  source(
    file.path(project_root, "engine", "R", relative_path),
    local = globalenv()
  )
}

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || is.na(a)[1]) b else a

read_oracle <- function(tag) {
  path <- file.path(public_data_dir, "oracle", "mlm", paste0(tag, ".json"))
  if (!file.exists(path)) return(NULL)
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

test_that("diary LMM reproduces the Bates sleepstudy fit (random slope, uncentered)", {
  data_path <- file.path(public_data_dir, "lme4", "sleepstudy.csv")
  oracle <- read_oracle("sleepstudy_lmer")
  skip_if(!file.exists(data_path) || is.null(oracle),
    "public sleepstudy validation assets absent")

  source_engine("lib/diary_utils.R")
  source_engine("lib/centering_utils.R")
  source_engine("lib/time_series_utils.R")
  source_engine("lib/diary_esm_evidence.R")
  source_engine("lib/diary_multilevel.R")

  data <- read.csv(data_path, check.names = FALSE)
  spec <- list(
    subjectVariableId = "Subject",
    timeVariableId = "Days",
    outcomeVariableId = "Reaction",
    predictorVariableId = "Days",
    analysisType = "lmm",
    randomSlope = TRUE,
    residualStructure = "independent",
    centering = "none",
    temporalEffect = "contemporaneous",
    lagOrder = NULL,
    level2CovariateIds = list(),
    controlVariableIds = list(),
    clusterStructure = "two_level",
    crossClassVariableId = NULL,
    missingStrategy = "none",
    runRobustnessChecks = FALSE,
    powerAnalysis = NULL,
    reliabilityConstructs = list(),
    excludeLowCompliance = FALSE,
    excludeOutOfWindow = FALSE
  )
  result <- fit_diary_multilevel(data, spec, function(id) id, 0.95)

  expect_true(isTRUE(result$available), info = "diary LMM must be available")
  expect_equal(result$sampleSize, 180L, info = "sleepstudy sample size")
  expect_equal(result$personCount, 18L, info = "sleepstudy person count")
  expect_true(isTRUE(result$randomSlope), info = "random slope declared")

  # fixed effects vs the canonical lme4 fit
  fixed_by_term <- stats::setNames(
    result$fixedEffects,
    vapply(result$fixedEffects, `[[`, character(1), "term")
  )
  for (row in oracle$fixed) {
    term <- row[["_row"]]
    engine_row <- fixed_by_term[[term]]
    expect_false(is.null(engine_row), info = paste0("diary LMM missing fixed term ", term))
    expect_equal(
      as.numeric(engine_row$estimate), as.numeric(row[["Estimate"]]),
      tolerance = 1e-6, info = paste0("diary LMM fixed effect ", term)
    )
    expect_equal(
      as.numeric(engine_row$standardError), as.numeric(row[["Std. Error"]]),
      tolerance = 1e-5, info = paste0("diary LMM fixed SE ", term)
    )
  }

  # variance components vs the canonical lme4 fit
  expect_equal(length(result$varianceComponents), length(oracle$ranef_var),
    info = "variance component count")
  for (oracle_row in oracle$ranef_var) {
    matches <- Filter(function(row) {
      identical(row$group, oracle_row$grp) &&
        identical(row$term %||% "", oracle_row$var1 %||% "") &&
        identical(row$pairedTerm %||% "", oracle_row$var2 %||% "")
    }, result$varianceComponents)
    expect_true(length(matches) == 1L,
      info = paste0("variance row ", oracle_row$grp, "/", oracle_row$var1 %||% "", "/", oracle_row$var2 %||% ""))
    matched <- matches[[1]]
    expect_equal(
      as.numeric(matched$variance), as.numeric(oracle_row$vcov),
      tolerance = 1e-4, info = paste0("variance for ", oracle_row$var1 %||% "residual")
    )
    if (!is.null(oracle_row$sdcor)) {
      expect_equal(
        as.numeric(matched$standardDeviation), as.numeric(oracle_row$sdcor),
        tolerance = 1e-4, info = paste0("sd for ", oracle_row$var1 %||% "residual")
      )
    }
  }

  # ICC from the frozen variance components
  subject_rows <- Filter(
    function(row) identical(row$grp, "Subject") && identical(row$var1, "(Intercept)") && is.null(row$var2),
    oracle$ranef_var
  )
  residual_rows <- Filter(function(row) identical(row$grp, "Residual"), oracle$ranef_var)
  subject_var <- subject_rows[[1]]$vcov
  residual_var <- residual_rows[[1]]$vcov
  expect_equal(
    as.numeric(result$icc), subject_var / (subject_var + residual_var),
    tolerance = 1e-6, info = "ICC matches frozen variance components"
  )
})
