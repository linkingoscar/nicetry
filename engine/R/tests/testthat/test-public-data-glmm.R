# Public-data GLMM validation: the diary/ESM GLMM path (fit_diary_glmm) vs
# direct lme4::glmer / glmmTMB fits on the canonical public datasets
# toenail (binary) and VerbAgg (count).

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "public-data-glmm.json")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

glmm_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
# lme4's bobyqa fit is mathematically the same model on the locked runtime,
# but its compiled BLAS/LAPACK path can move the last optimizer digits between
# Windows binaries. The frozen oracle records field-specific absolute bounds
# for that documented cross-platform numerical drift; it does not change the
# model, estimator, or interpretation boundary.
glmm_tolerance <- glmm_oracle$provenance$tolerance
label_for <- function(id) id

source_engine("lib/diary_utils.R")
source_engine("lib/seed_utils.R")
source_engine("lib/centering_utils.R")
source_engine("lib/time_series_utils.R")
source_engine("lib/diary_esm_evidence.R")
source_engine("lib/diary_multilevel.R")
source_engine("lib/diary_glmm.R")

compare_glmm <- function(result, golden, label) {
  expect_equal(result$sampleSize, golden$sampleSize, info = paste0(label, ": sample size"))
  expect_equal(result$personCount, golden$personCount, info = paste0(label, ": person count"))

  engine_by_term <- stats::setNames(result$fixedEffects,
    vapply(result$fixedEffects, `[[`, character(1), "term"))
  expect_equal(length(result$fixedEffects), length(golden$fixedEffects),
    info = paste0(label, ": fixed effect count"))
  for (row in golden$fixedEffects) {
    engine_row <- engine_by_term[[row$term]]
    expect_false(is.null(engine_row), info = paste0(label, ": missing term ", row$term))
    expect_equal(as.numeric(engine_row$estimate), row$estimate,
      tolerance = glmm_tolerance$estimate, info = paste0(label, ": est ", row$term))
    expect_equal(as.numeric(engine_row$standardError), row$standardError,
      tolerance = glmm_tolerance$se, info = paste0(label, ": se ", row$term))
    expect_equal(as.numeric(engine_row$pValue), row$pValue,
      tolerance = glmm_tolerance$pValue, info = paste0(label, ": p ", row$term))
    expect_equal(as.numeric(engine_row$exponentiatedEstimate), row$exponentiatedEstimate,
      tolerance = glmm_tolerance$estimate, info = paste0(label, ": exp(est) ", row$term))
  }

  expect_equal(length(result$varianceComponents), length(golden$varianceComponents),
    info = paste0(label, ": variance component count"))
  for (golden_row in golden$varianceComponents) {
    matches <- Filter(function(row) {
      identical(row$group, golden_row$group) &&
        identical(row$term %||% "", golden_row$term %||% "") &&
        identical(row$pairedTerm %||% "", golden_row$pairedTerm %||% "")
    }, result$varianceComponents)
    expect_true(length(matches) == 1L,
      info = paste0(label, ": variance row ", golden_row$group, "/", golden_row$term %||% ""))
    matched <- matches[[1]]
    if (!is.null(golden_row$variance)) {
      expect_equal(as.numeric(matched$variance), golden_row$variance,
        tolerance = glmm_tolerance$variance,
        info = paste0(label, ": variance ", golden_row$term %||% "residual"))
    }
    if (!is.null(golden_row$standardDeviation)) {
      expect_equal(as.numeric(matched$standardDeviation), golden_row$standardDeviation,
        tolerance = glmm_tolerance$variance,
        info = paste0(label, ": sd ", golden_row$term %||% "residual"))
    }
  }
  invisible(TRUE)
}

`%||%` <- function(a, b) if (is.null(a) || length(a) == 0 || is.na(a)[1]) b else a

test_that("binary GLMM (toenail) matches lme4::glmer", {
  skip_if(is.null(glmm_oracle), "public GLMM oracle absent")
  data <- lme4::toenail
  data$outcome <- as.integer(data$outcome == "moderate or severe")
  data$patientID <- as.factor(data$patientID)
  spec <- list(
    subjectVariableId = "patientID",
    timeVariableId = "visit",
    outcomeVariableId = "outcome",
    predictorVariableId = "treatment",
    controlVariableIds = "time",
    level2CovariateIds = list(),
    outcomeFamily = "binomial",
    countModel = "standard",
    zeroProcessPredictors = "intercept_only",
    exposureVariableId = NULL,
    randomSlope = FALSE,
    residualStructure = "independent",
    centering = "none",
    temporalEffect = "contemporaneous",
    lagOrder = NULL,
    clusterStructure = "two_level",
    crossClassVariableId = NULL,
    distributionDiagnosticSimulations = 250L,
    distributionDiagnosticSeed = 20260729L
  )
  result <- fit_diary_glmm(data, spec, label_for, 0.95)
  expect_true(isTRUE(result$available), info = "toenail GLMM available")
  expect_identical(result$linkFunction, "logit")
  compare_glmm(result, glmm_oracle$toenail, "toenail")
})

test_that("count GLMM (grouseticks, Poisson) matches glmmTMB", {
  skip_if(is.null(glmm_oracle), "public GLMM oracle absent")
  data <- lme4::grouseticks
  data$INDEX <- as.numeric(as.character(data$INDEX))
  spec <- list(
    subjectVariableId = "BROOD",
    timeVariableId = "INDEX",
    outcomeVariableId = "TICKS",
    predictorVariableId = "HEIGHT",
    controlVariableIds = "YEAR",
    level2CovariateIds = list(),
    outcomeFamily = "poisson",
    countModel = "standard",
    zeroProcessPredictors = "intercept_only",
    exposureVariableId = NULL,
    randomSlope = FALSE,
    residualStructure = "independent",
    centering = "none",
    temporalEffect = "contemporaneous",
    lagOrder = NULL,
    clusterStructure = "two_level",
    crossClassVariableId = NULL,
    distributionDiagnosticSimulations = 250L,
    distributionDiagnosticSeed = 20260729L
  )
  result <- fit_diary_glmm(data, spec, label_for, 0.95)
  expect_true(isTRUE(result$available), info = "VerbAgg GLMM available")
  expect_identical(result$linkFunction, "log")
  compare_glmm(result, glmm_oracle$verbagg, "verbagg")
})
