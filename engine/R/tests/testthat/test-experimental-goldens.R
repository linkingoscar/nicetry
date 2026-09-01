# Golden test: experimental-design workbench vs afex/emmeans direct fits on
# deterministic synthetic designs (2x2 factorial + covariate; single-factor
# 3-level with planned contrasts). The engine entry (run_advanced_analysis.R,
# family experimental_design) wraps afex::aov_car + emmeans; this validates
# the spec->formula/EMM/contrast plumbing against the frozen oracle.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "experimental-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
exp_data_dir <- file.path(data_dir, "experimental")

experimental_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
exp_tolerance <- experimental_oracle$provenance$tolerance

run_engine_experimental <- function(tag, spec, csv_name, work_dir) {
  input_path <- file.path(work_dir, "input.json")
  output_path <- file.path(work_dir, "output.json")
  writeLines(
    jsonlite::toJSON(list(
      spec = spec,
      dataPath = file.path(exp_data_dir, csv_name),
      progressPath = file.path(work_dir, "progress.json"),
      cancelPath = file.path(work_dir, "cancel.json")
    ), auto_unbox = TRUE, digits = NA),
    input_path
  )
  runner <- file.path(project_root, "engine", "R", "run_advanced_analysis.R")
  rscript <- file.path(R.home("bin"), "Rscript.exe")
  status <- system2(
    rscript, c("--vanilla", shQuote(runner), shQuote(input_path), shQuote(output_path)),
    stdout = TRUE, stderr = TRUE
  )
  if (!file.exists(output_path)) {
    stop("run_advanced_analysis.R experimental failed for ", tag, ": ",
      paste(status, collapse = "\n"))
  }
  jsonlite::fromJSON(output_path, simplifyVector = FALSE)
}

base_experimental_spec <- function() {
  list(
    family = "experimental_design",
    analysisType = "factorial_anova",
    designType = "factorial_anova",
    dataLayout = "long",
    sumOfSquares = "III",
    postHocAdjustment = "holm",
    homogeneityOfSlopes = "check_and_warn",
    confidenceLevel = 0.95,
    seed = 20260730
  )
}

test_that("2x2 factorial + covariate matches afex/emmeans", {
  skip_if(is.null(experimental_oracle) ||
    !file.exists(file.path(exp_data_dir, "exp_2x2_cov.csv")),
    "experimental golden assets absent")
  work <- tempfile("rp-experimental-22-"); dir.create(work)
  spec <- base_experimental_spec()
  spec$outcomeIds <- "y"
  spec$subjectId <- "subject"
  spec$betweenFactors <- list(
    list(variableId = "A", coding = "sum"),
    list(variableId = "B", coding = "sum")
  )
  spec$covariateIds <- "cov"
  result <- run_engine_experimental("factorial2x2", spec, "exp_2x2_cov.csv", work)
  family_result <- result$familyResult
  golden <- experimental_oracle$factorial2x2

  engine_omnibus <- stats::setNames(family_result$omnibusTests,
    vapply(family_result$omnibusTests, `[[`, character(1), "term"))
  expect_equal(length(engine_omnibus), length(golden$omnibus),
    info = "omnibus count")
  for (row in golden$omnibus) {
    engine_row <- engine_omnibus[[row$term]]
    expect_false(is.null(engine_row), info = paste0("omnibus term ", row$term))
    expect_equal(as.numeric(engine_row$f), row$f,
      tolerance = exp_tolerance$omnibus, info = paste0("F ", row$term))
    expect_equal(as.numeric(engine_row$pValue), row$pValue,
      tolerance = exp_tolerance$omnibus, info = paste0("p ", row$term))
    expect_equal(as.numeric(engine_row$partialEtaSquared), row$partialEtaSquared,
      tolerance = exp_tolerance$omnibus, info = paste0("pes ", row$term))
    if (!is.null(row$numeratorDf)) {
      expect_equal(as.numeric(engine_row$numeratorDf), row$numeratorDf,
        info = paste0("numDf ", row$term))
    }
  }

  engine_emm <- family_result$estimatedMarginalMeans
  expect_equal(length(engine_emm), length(golden$emm), info = "EMM count")
  for (index in seq_along(golden$emm)) {
    grow <- golden$emm[[index]]
    erow <- engine_emm[[index]]
    expect_equal(as.numeric(erow$emmean), as.numeric(grow$emmean),
      tolerance = exp_tolerance$emm, info = paste0("EMM ", index))
    expect_equal(as.numeric(erow$SE), as.numeric(grow$SE),
      tolerance = exp_tolerance$emm, info = paste0("EMM SE ", index))
  }

  expect_equal(length(family_result$contrasts), length(golden$contrasts),
    info = "contrast count")
  for (index in seq_along(golden$contrasts)) {
    grow <- golden$contrasts[[index]]
    erow <- family_result$contrasts[[index]]
    expect_equal(as.numeric(erow$estimate), grow$estimate,
      tolerance = exp_tolerance$contrast, info = paste0("contrast est ", index))
    expect_equal(as.numeric(erow$SE), grow$standardError,
      tolerance = exp_tolerance$contrast, info = paste0("contrast SE ", index))
    expect_equal(as.numeric(erow$p.value), grow$pValue,
      tolerance = exp_tolerance$contrast, info = paste0("contrast p ", index))
  }
})

test_that("single-factor 3-level with planned contrasts matches afex/emmeans", {
  skip_if(is.null(experimental_oracle) ||
    !file.exists(file.path(exp_data_dir, "exp_1f3.csv")),
    "experimental golden assets absent")
  work <- tempfile("rp-experimental-1f-"); dir.create(work)
  spec <- base_experimental_spec()
  spec$outcomeIds <- "y"
  spec$subjectId <- "subject"
  spec$betweenFactors <- list(list(variableId = "F", coding = "sum"))
  spec$plannedContrasts <- list(
    list(id = "c1", weights = list(f1 = -1, f2 = 1, f3 = 0), multiplicityFamilyId = "famA"),
    list(id = "c2", weights = list(f1 = -0.5, f2 = -0.5, f3 = 1), multiplicityFamilyId = "famA")
  )
  result <- run_engine_experimental("singleFactor3", spec, "exp_1f3.csv", work)
  family_result <- result$familyResult
  golden <- experimental_oracle$singleFactor3

  engine_omnibus <- stats::setNames(family_result$omnibusTests,
    vapply(family_result$omnibusTests, `[[`, character(1), "term"))
  for (row in golden$omnibus) {
    engine_row <- engine_omnibus[[row$term]]
    expect_false(is.null(engine_row), info = paste0("omnibus term ", row$term))
    expect_equal(as.numeric(engine_row$f), row$f,
      tolerance = exp_tolerance$omnibus, info = paste0("F ", row$term))
    expect_equal(as.numeric(engine_row$pValue), row$pValue,
      tolerance = exp_tolerance$omnibus, info = paste0("p ", row$term))
  }

  expect_equal(length(family_result$contrasts), length(golden$contrasts),
    info = "contrast count")
  for (index in seq_along(golden$contrasts)) {
    grow <- golden$contrasts[[index]]
    erow <- family_result$contrasts[[index]]
    expect_equal(as.numeric(erow$estimate), grow$estimate,
      tolerance = exp_tolerance$contrast, info = paste0("contrast est ", index))
    expect_equal(as.numeric(erow$SE), grow$standardError,
      tolerance = exp_tolerance$contrast, info = paste0("contrast SE ", index))
    expect_equal(as.numeric(erow$p.value), grow$pValue,
      tolerance = exp_tolerance$contrast, info = paste0("contrast p ", index))
  }

  engine_planned <- stats::setNames(family_result$plannedContrasts,
    vapply(family_result$plannedContrasts, `[[`, character(1), "plannedContrastId"))
  expect_equal(length(engine_planned), length(golden$plannedContrasts),
    info = "planned contrast count")
  for (row in golden$plannedContrasts) {
    engine_row <- engine_planned[[row$plannedContrastId]]
    expect_false(is.null(engine_row),
      info = paste0("planned contrast ", row$plannedContrastId))
    expect_equal(as.numeric(engine_row$estimate), row$estimate,
      tolerance = exp_tolerance$contrast,
      info = paste0("planned est ", row$plannedContrastId))
    expect_equal(as.numeric(engine_row$SE), row$standardError,
      tolerance = exp_tolerance$contrast,
      info = paste0("planned SE ", row$plannedContrastId))
    expect_equal(as.numeric(engine_row$p.value), row$pValue,
      tolerance = exp_tolerance$contrast,
      info = paste0("planned p (holm) ", row$plannedContrastId))
  }
})
