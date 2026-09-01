# Golden test: PROCESS binary-Y logistic path vs the official macro (log-odds
# equations, direct/indirect effects, bootstrap CI) and hand-written average
# marginal effects, on deterministic synthetic data.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "logistic-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
logistic_data_path <- file.path(data_dir, "logistic", "logistic_data.csv")

logistic_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
logistic_tolerance <- logistic_oracle$provenance$tolerance

test_that("binary-Y model 4 matches the official macro and hand-written AME", {
  skip_if(is.null(logistic_oracle) || !file.exists(logistic_data_path),
    "logistic golden assets absent")
  work <- tempfile("rp-logistic-"); dir.create(work)
  spec <- list(
    schemaVersion = "1.0.0",
    modelId = "logistic_golden_v1",
    name = "logistic validation",
    datasetVersionId = "logistic_golden_v1",
    design = list(timeStructure = "cross_sectional", clustering = "none", claimMode = "associational"),
    nodes = list(
      list(id = "x", variableId = "var_x", label = "X", kind = "observed", role = "x", dataType = "continuous"),
      list(id = "m1", variableId = "var_m1", label = "M", kind = "observed", role = "m", dataType = "continuous"),
      list(id = "y", variableId = "var_y", label = "Y", kind = "observed", role = "y", dataType = "binary",
           encoding = list(method = "binary_indicator"))
    ),
    edges = list(
      list(id = "edge_x_m1", from = "x", to = "m1", kind = "regression"),
      list(id = "edge_m1_y", from = "m1", to = "y", kind = "regression"),
      list(id = "edge_x_y", from = "x", to = "y", kind = "regression")
    ),
    moderations = list(),
    covariates = list(),
    estimation = list(
      family = "logistic",
      standardErrors = "classical",
      confidenceLevel = 0.95,
      bootstrap = list(enabled = TRUE, replicates = 5000, method = "percentile", seed = 31216),
      missing = "complete_cases_per_model",
      centering = list(method = "none", nodeIds = list()),
      reportScale = "unstandardized_primary"
    )
  )
  input_path <- file.path(work, "input.json")
  output_path <- file.path(work, "output.json")
  writeLines(
    jsonlite::toJSON(list(
      modelSpec = spec,
      dataPath = logistic_data_path,
      processModelNumber = 4,
      progressPath = file.path(work, "progress.json"),
      cancelPath = file.path(work, "cancel.json")
    ), auto_unbox = TRUE, digits = NA),
    input_path
  )
  runner <- file.path(project_root, "engine", "R", "run_analysis.R")
  rscript <- file.path(R.home("bin"), "Rscript.exe")
  status <- system2(
    rscript, c("--vanilla", shQuote(runner), shQuote(input_path), shQuote(output_path)),
    stdout = TRUE, stderr = TRUE
  )
  if (!file.exists(output_path)) {
    stop("run_analysis.R logistic failed: ", paste(status, collapse = "\n"))
  }
  result <- jsonlite::fromJSON(output_path, simplifyVector = FALSE)

  engine_equations <- stats::setNames(result$equations,
    vapply(result$equations, function(equation) {
      trimws(strsplit(equation$formula, "~", fixed = TRUE)[[1]][1])
    }, character(1)))

  # M equation (OLS)
  engine_m <- stats::setNames(engine_equations[["m1"]]$coefficients,
    vapply(engine_equations[["m1"]]$coefficients, `[[`, character(1), "term"))
  for (row in logistic_oracle$equations$m1) {
    engine_term <- if (row$term == "constant") "(Intercept)" else sub("^var_", "", row$term)
    expect_equal(as.numeric(engine_m[[engine_term]]$estimate), row$coeff,
      tolerance = logistic_tolerance$coefficient,
      info = paste0("M equation ", row$term))
  }

  # Y equation (logit)
  engine_y <- stats::setNames(engine_equations[["y"]]$coefficients,
    vapply(engine_equations[["y"]]$coefficients, `[[`, character(1), "term"))
  for (row in logistic_oracle$equations$y) {
    engine_term <- if (row$term == "constant") "(Intercept)" else sub("^var_", "", row$term)
    engine_row <- engine_y[[engine_term]]
    expect_equal(as.numeric(engine_row$estimate), row$coeff,
      tolerance = logistic_tolerance$coefficient,
      info = paste0("Y equation ", row$term))
    expect_equal(as.numeric(engine_row$standardError), row$se,
      tolerance = 1e-6, info = paste0("Y SE ", row$term))
    expect_equal(as.numeric(engine_row$pValue), row$p,
      tolerance = 1e-6, info = paste0("Y p ", row$term))
  }

  # AME: hand-written derivative average marginal effects
  for (ame_row in logistic_oracle$averageMarginalEffects) {
    engine_term <- sub("^var_", "", ame_row$term)
    engine_row <- engine_y[[engine_term]]
    expect_false(is.null(engine_row$averageMarginalEffect),
      info = paste0("AME missing for ", engine_term))
    expect_equal(as.numeric(engine_row$averageMarginalEffect), ame_row$estimate,
      tolerance = logistic_tolerance$ame, info = paste0("AME ", engine_term))
  }

  # direct + indirect (log-odds metric)
  direct <- Filter(function(effect) effect$type == "direct", result$effects)[[1]]
  expect_equal(unname(direct$estimate), logistic_oracle$direct$effect,
    tolerance = logistic_tolerance$effect, info = "direct effect (log-odds)")
  indirect <- Filter(function(effect) effect$type == "indirect", result$effects)[[1]]
  expect_equal(unname(indirect$estimate), logistic_oracle$indirect$effect,
    tolerance = logistic_tolerance$effect, info = "indirect effect (log-odds)")
  interval <- indirect$confidenceInterval
  expect_equal(interval$lower, logistic_oracle$indirect$bootLLCI,
    tolerance = logistic_tolerance$bootstrapInterval, info = "indirect boot lower")
  expect_equal(interval$upper, logistic_oracle$indirect$bootULCI,
    tolerance = logistic_tolerance$bootstrapInterval, info = "indirect boot upper")
})
