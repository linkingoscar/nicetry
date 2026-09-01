test_that("selected correlation never invokes unrelated estimators", {
  work <- tempfile("procedure-isolation-")
  dir.create(work)
  on.exit(unlink(work, recursive = TRUE), add = TRUE)
  frame <- data.frame(x = seq_len(30), y = seq_len(30) %% 2)
  csv <- file.path(work, "data.csv")
  write.csv(frame, csv, row.names = FALSE)
  input <- file.path(work, "input.json")
  output <- file.path(work, "result.json")
  main <- file.path(project_root, "engine", "R", "run_empirical_analysis.R")
  jsonlite::write_json(list(
    dataPath = csv, reportId = "empirical_1234567890abcdef", datasetId = "fixture",
    measurementVersionId = "fixture-v1", createdAt = "2026-08-31",
    metadata = list(
      variables = list(list(id = "x", type = "continuous", label = "X"), list(id = "y", type = "binary", label = "Y")),
      constructs = list(list(id = "construct", label = "X", scoreId = "x", itemIds = list("x")))
    ),
    options = list(procedure = "correlation", analysisVariableIds = list("x", "y"),
      confidenceLevel = 0.95, correlationMethod = "pearson", correlationPAdjust = "BH",
      multiplicityPAdjust = "BH", controlVariableIds = list(), randomSeed = 1,
      contextTimeStructure = "cross_sectional", contextDependenceStructure = "independent")
  ), input, auto_unbox = TRUE)
  run_environment <- new.env(parent = globalenv())
  run_environment$commandArgs <- function(trailingOnly = FALSE) {
    if (trailingOnly) c(input, output) else paste0("--file=", main)
  }
  forbidden <- c("run_empirical_cfa", "fit_ulmc_cmb_model", "empirical_fit_efa_block",
    "htmt_bootstrap", "fit_hierarchical_regression", "fit_empirical_group_comparison",
    "build_construct_validity", "fit_longitudinal_panel", "fit_diary_multilevel")
  run_environment$source <- function(file, local, ...) {
    base::sys.source(file, envir = local)
    for (name in forbidden) local[[name]] <- function(...) stop("Unselected estimator invoked")
  }
  expect_error(base::sys.source(main, envir = run_environment), NA)
  result <- jsonlite::read_json(output, simplifyVector = FALSE)
  expect_equal(unlist(lapply(result$correlations$variables, `[[`, "id")), c("x", "y"))
  expect_equal(result$correlations$coefficients[[1]][[2]], cor(frame$x, frame$y), tolerance = 1e-8)
  expect_identical(result$cfa$reason, "not_requested")
  expect_identical(result$efa$reason, "not_requested")
  expect_equal(result$provenance$htmtBootstrap$replicates, 0)
  frame$y <- rep(c("yes", "no"), 15)
  write.csv(frame, csv, row.names = FALSE)
  expect_error(base::sys.source(main, envir = run_environment), "数值编码")
})
