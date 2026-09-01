# Golden test: multiple imputation + Rubin pooling vs mice + hand-written
# Barnard-Rubin formulas on Hayes' glbwarm data with deterministic MCAR holes.
#
# The engine (run_advanced_analysis.R, family multiple_imputation) runs
# mice::mice and pool_rubin_estimates; the oracle performs the identical
# imputation call and pools with independently written textbook formulas.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "mi-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
mi_data_path <- file.path(data_dir, "mi", "glbwarm_missing.csv")

mi_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
mi_tolerance <- mi_oracle$provenance$tolerance

test_that("Rubin pooling matches hand-written Barnard-Rubin formulas", {
  skip_if(is.null(mi_oracle) || !file.exists(mi_data_path),
    "MI golden assets absent")
  work <- tempfile("rp-mi-"); dir.create(work)
  artifact_dir <- file.path(work, "artifacts")
  dir.create(artifact_dir)
  spec <- list(
    family = "multiple_imputation",
    datasetVersionId = "mi_golden_v1",
    method = "auto",
    imputations = 10,
    iterations = 5,
    variables = list(
      list(variableId = "negemot", method = "pmm",
           predictorIds = c("posemot", "age", "ideology", "sex", "govact")),
      list(variableId = "posemot", method = "pmm",
           predictorIds = c("negemot", "age", "ideology")),
      list(variableId = "age", method = "pmm",
           predictorIds = c("negemot", "posemot"))
    ),
    passiveRules = list(),
    pooling = "rubin",
    pooledAnalysis = list(
      modelType = "linear_regression",
      outcomeId = "govact",
      predictorIds = c("negemot", "age", "sex"),
      includeIntercept = TRUE
    ),
    substantiveModelHash = "mi-golden-v1",
    diagnostics = list(),
    confidenceLevel = 0.95,
    seed = 20260814
  )
  input_path <- file.path(work, "input.json")
  output_path <- file.path(work, "output.json")
  writeLines(
    jsonlite::toJSON(list(
      spec = spec,
      dataPath = mi_data_path,
      artifactDirectory = artifact_dir,
      progressPath = file.path(work, "progress.json"),
      cancelPath = file.path(work, "cancel.json")
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
    stop("run_advanced_analysis.R MI failed: ", paste(status, collapse = "\n"))
  }
  result <- jsonlite::fromJSON(output_path, simplifyVector = FALSE)

  engine_rows <- stats::setNames(result$familyResult$rubin$estimates,
    vapply(result$familyResult$rubin$estimates, `[[`, character(1), "term"))
  expect_equal(length(engine_rows), length(mi_oracle$estimates),
    info = "pooled estimate count")
  for (golden_row in mi_oracle$estimates) {
    engine_row <- engine_rows[[golden_row$term]]
    expect_false(is.null(engine_row), info = paste0("pooled term ", golden_row$term))
    expect_equal(as.numeric(engine_row$estimate), golden_row$estimate,
      tolerance = mi_tolerance$estimate, info = paste0("est ", golden_row$term))
    expect_equal(as.numeric(engine_row$standardError), golden_row$standardError,
      tolerance = mi_tolerance$se, info = paste0("SE ", golden_row$term))
    expect_equal(as.numeric(engine_row$degreesOfFreedom), golden_row$degreesOfFreedom,
      tolerance = mi_tolerance$df, info = paste0("df ", golden_row$term))
    expect_equal(as.numeric(engine_row$statistic), golden_row$statistic,
      tolerance = mi_tolerance$statistic, info = paste0("t ", golden_row$term))
    expect_equal(as.numeric(engine_row$pValue), golden_row$pValue,
      tolerance = mi_tolerance$pValue, info = paste0("p ", golden_row$term))
    expect_equal(as.numeric(engine_row$confidenceLower), golden_row$confidenceLower,
      tolerance = mi_tolerance$estimate, info = paste0("CI lower ", golden_row$term))
    expect_equal(as.numeric(engine_row$confidenceUpper), golden_row$confidenceUpper,
      tolerance = mi_tolerance$estimate, info = paste0("CI upper ", golden_row$term))
    expect_equal(as.numeric(engine_row$withinVariance), golden_row$withinVariance,
      tolerance = mi_tolerance$variance, info = paste0("within var ", golden_row$term))
    expect_equal(as.numeric(engine_row$betweenVariance), golden_row$betweenVariance,
      tolerance = mi_tolerance$variance, info = paste0("between var ", golden_row$term))
    expect_equal(as.numeric(engine_row$totalVariance), golden_row$totalVariance,
      tolerance = mi_tolerance$variance, info = paste0("total var ", golden_row$term))
    expect_equal(as.numeric(engine_row$RIV), golden_row$RIV,
      tolerance = mi_tolerance$rivFmi, info = paste0("RIV ", golden_row$term))
    expect_equal(as.numeric(engine_row$FMI), golden_row$FMI,
      tolerance = mi_tolerance$rivFmi, info = paste0("FMI ", golden_row$term))
  }

  # artifacts: one completed CSV per imputation, reproducible content
  artifacts <- result$familyResult$artifacts
  expect_equal(length(artifacts), 10L, info = "imputation artifact count")
  expect_true(all(file.exists(file.path(artifact_dir, vapply(artifacts,
    `[[`, character(1), "temporary")))), info = "imputation artifacts written")
})
