# Public-data MLM oracle tests: the engine's advanced two-level Gaussian LMM
# (run_advanced_analysis.R, multilevel_model family) vs lme4/lmerTest textbook
# fits on the same frozen reference data.
#
# Oracle values live in output/validation-datasets/oracle/mlm/*.json (generated
# by lme4 on the canonical datasets; see REFERENCE.md). When the datasets are
# absent the tests skip. Both sides fit IDENTICAL models (same formula space,
# same REML estimator) so tolerances are tight, not statistical.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
public_data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
mlm_oracle_dir <- file.path(public_data_dir, "oracle", "mlm")

read_oracle <- function(tag) {
  path <- file.path(mlm_oracle_dir, paste0(tag, ".json"))
  if (!file.exists(path)) return(NULL)
  jsonlite::fromJSON(path, simplifyVector = FALSE)
}

mlm_tolerance <- list(estimate = 1e-6, se = 1e-5, variance = 1e-4, fitIndex = 1e-4)

mlm_spec <- function(outcome, cluster, fixed, random, seed = 20260814) {
  list(
    family = "multilevel_model",
    analysisType = "lmm",
    datasetVersionId = "public_mlm_validation",
    outcomeId = outcome,
    distribution = "gaussian",
    clusterVariableId = cluster,
    fixedEffectIds = as.list(fixed),
    randomEffects = random,
    centering = list(),
    estimator = "REML",
    degreesOfFreedom = "satterthwaite",
    minimumClusterCount = 10L,
    confidenceLevel = 0.95,
    seed = seed
  )
}

random_intercept <- function(grouping) {
  list(list(groupingVariableId = grouping, intercept = TRUE, slopeVariableIds = list(), covariance = "correlated"))
}

run_engine_mlm <- function(tag, spec, data_path, work_dir) {
  input_path <- file.path(work_dir, "input.json")
  output_path <- file.path(work_dir, "output.json")
  writeLines(
    jsonlite::toJSON(
      list(spec = spec, dataPath = data_path,
           progressPath = file.path(work_dir, "progress.json"),
           cancelPath = file.path(work_dir, "cancel.json")),
      auto_unbox = TRUE, digits = NA
    ),
    input_path
  )
  runner <- file.path(project_root, "engine", "R", "run_advanced_analysis.R")
  rscript <- file.path(R.home("bin"), "Rscript.exe")
  status <- system2(
    rscript, c("--vanilla", shQuote(runner), shQuote(input_path), shQuote(output_path)),
    stdout = TRUE, stderr = TRUE
  )
  if (!file.exists(output_path)) {
    stop("run_advanced_analysis.R failed for ", tag, ": ", paste(status, collapse = "\n"))
  }
  jsonlite::fromJSON(output_path, simplifyVector = FALSE)
}

check_mlm <- function(tag, spec, result) {
  oracle <- read_oracle(tag)
  expect_false(is.null(oracle), info = paste0(tag, ": oracle JSON missing"))

  # fixed effects: estimate + asymptotic SE must match lme4 exactly
  engine_estimates <- stats::setNames(result$estimates, vapply(result$estimates, `[[`, character(1), "id"))
  for (row in oracle$fixed) {
    term <- row[["_row"]]
    engine_row <- engine_estimates[[term]]
    expect_false(is.null(engine_row), info = paste0(tag, ": engine missing fixed term ", term))
    expect_equal(
      as.numeric(engine_row$estimate), as.numeric(row[["Estimate"]]),
      tolerance = mlm_tolerance$estimate,
      info = paste0(tag, ": fixed effect ", term)
    )
    expect_equal(
      as.numeric(engine_row$standardError), as.numeric(row[["Std. Error"]]),
      tolerance = mlm_tolerance$se,
      info = paste0(tag, ": fixed SE ", term)
    )
  }

  # variance components: grp/var1/var2/vcov rows
  engine_vc <- result$familyResult$varianceComponents
  oracle_vc <- oracle$ranef_var
  expect_equal(length(engine_vc), length(oracle_vc), info = paste0(tag, ": variance component count"))
  for (oracle_row in oracle_vc) {
    matches <- Filter(function(row) {
      identical(row$grp, oracle_row$grp) &&
        identical(row$var1 %||% "", oracle_row$var1 %||% "") &&
        identical(row$var2 %||% "", oracle_row$var2 %||% "")
    }, engine_vc)
    expect_true(
      length(matches) == 1L,
      info = paste0(tag, ": variance row ", oracle_row$grp, "/", oracle_row$var1 %||% "", "/", oracle_row$var2 %||% "", " (", length(matches), " matches)")
    )
    matched <- matches[[1]]
    expect_equal(
      as.numeric(matched$vcov), as.numeric(oracle_row$vcov),
      tolerance = mlm_tolerance$variance,
      info = paste0(tag, ": vcov for ", oracle_row$var1 %||% "residual")
    )
  }

  # fit indices
  engine_fit <- result$familyResult$fitIndices
  for (key in c("AIC", "BIC", "logLik")) {
    expect_equal(
      as.numeric(engine_fit[[key]]), as.numeric(oracle$fitIndices[[key]]),
      tolerance = mlm_tolerance$fitIndex,
      info = paste0(tag, ": ", key)
    )
  }
  invisible(TRUE)
}

`%||%` <- function(a, b) if (is.null(a)) b else a

skip_unless_public <- function(path) {
  skip_if(!file.exists(path), paste0("public validation data absent: ", path))
}

# --- Raudenbush & Bryk HSB: mathach ~ meanses + cses + (1|school) --------------

test_that("Hsb82 two-level model matches lme4 textbook fit (meanses + cses)", {
  data_path <- file.path(public_data_dir, "Hsb82.csv")
  skip_unless_public(data_path)
  work <- tempfile("rp-public-hsb-"); dir.create(work)
  spec <- mlm_spec("mAch", "school", c("meanses", "cses"), random_intercept("school"))
  result <- run_engine_mlm("Hsb82_lmer_meanses_cses", spec, data_path, work)
  check_mlm("Hsb82_lmer_meanses_cses", spec, result)
})

# --- Bates sleepstudy: Reaction ~ Days + (1 + Days | Subject) ------------------

test_that("sleepstudy random-slope model matches lme4 canonical fit", {
  data_path <- file.path(public_data_dir, "lme4", "sleepstudy.csv")
  skip_unless_public(data_path)
  work <- tempfile("rp-public-sleep-"); dir.create(work)
  random <- list(list(
    groupingVariableId = "Subject", intercept = TRUE,
    slopeVariableIds = list("Days"), covariance = "correlated"
  ))
  spec <- mlm_spec("Reaction", "Subject", c("Days"), random)
  result <- run_engine_mlm("sleepstudy_lmer", spec, data_path, work)
  check_mlm("sleepstudy_lmer", spec, result)
})

# --- Snijders & Bosker Exam: normexam ~ standLRT + sex + schgend + (1|school) ---

test_that("Exam school-effects model matches lme4 fit", {
  data_path <- file.path(public_data_dir, "Exam.csv")
  skip_unless_public(data_path)
  work <- tempfile("rp-public-exam-"); dir.create(work)
  spec <- mlm_spec("normexam", "school", c("standLRT", "sex", "schgend"), random_intercept("school"))
  result <- run_engine_mlm("Exam_lmer", spec, data_path, work)
  check_mlm("Exam_lmer", spec, result)
})
