# Golden test: IRT/DIF workbench vs direct mirt fits + parameter recovery
# against the KNOWN generating parameters on deterministic simulations.
#
# Two layers:
#  - plumbing: engine item parameters and DIF LRTs equal the frozen direct
#    mirt / replicated-LRT oracle exactly (same calls);
#  - science: recovered parameters land within 3*SE + 0.1 of the generating
#    values, and the true-DIF item is detected while clean items are not.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "irt-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
irt_dir <- file.path(data_dir, "irt")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

irt_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
irt_tolerance <- irt_oracle$provenance$tolerance

source_engine("lib/runtime.R")
source_engine("lib/esem_bifactor.R")

test_that("2PL item parameters match mirt and recover the generating values", {
  skip_if(is.null(irt_oracle) || !file.exists(file.path(irt_dir, "irt_2pl.csv")),
    "IRT golden assets absent")
  items <- read.csv(file.path(irt_dir, "irt_2pl.csv"), check.names = FALSE)
  groups <- read.csv(file.path(irt_dir, "groups.csv"), check.names = FALSE)$group
  result <- fit_irt_dif_model(
    items, list(list(id = "c", itemIds = paste0("i", seq_len(5)))),
    group_variable = groups, requested_model = "2PL"
  )
  expect_true(isTRUE(result$available), info = "2PL IRT must be available")
  expect_identical(result$executedIrtModel, "2PL")

  engine_params <- stats::setNames(result$itemParameters,
    vapply(result$itemParameters, `[[`, character(1), "itemId"))
  for (i in seq_along(irt_oracle$mirt2PL)) {
    oracle_row <- irt_oracle$mirt2PL[[i]]
    id <- oracle_row$itemId
    engine_row <- engine_params[[id]]
    expect_equal(as.numeric(engine_row$discrimination), as.numeric(oracle_row$estimate$a),
      tolerance = irt_tolerance$estimate, info = paste0(id, ": a vs mirt"))
    expect_equal(as.numeric(unlist(engine_row$difficulties)), as.numeric(oracle_row$estimate$b),
      tolerance = irt_tolerance$estimate, info = paste0(id, ": b vs mirt"))

    true_a <- irt_oracle$true2PL$a[[i]]
    true_b <- irt_oracle$true2PL$b[[i]]
    bound_a <- 3 * as.numeric(oracle_row$standardError$a) + 0.1
    bound_b <- 3 * as.numeric(oracle_row$standardError$b) + 0.1
    expect_true(abs(as.numeric(oracle_row$estimate$a) - true_a) <= bound_a,
      info = paste0(id, ": recovery of a (", oracle_row$estimate$a, " vs true ", true_a, ")"))
    expect_true(abs(as.numeric(oracle_row$estimate$b[[1]]) - true_b) <= bound_b,
      info = paste0(id, ": recovery of b (", oracle_row$estimate$b[[1]], " vs true ", true_b, ")"))
  }

  # DIF: plumbing + detection behavior
  expect_identical(result$difStatus, "available")
  engine_dif <- stats::setNames(result$difAnalysis,
    vapply(result$difAnalysis, `[[`, character(1), "itemId"))
  for (oracle_row in irt_oracle$dif2PL) {
    engine_row <- engine_dif[[oracle_row$itemId]]
    expect_equal(as.numeric(engine_row$statistic), oracle_row$statistic,
      tolerance = irt_tolerance$dif, info = paste0(oracle_row$itemId, ": DIF statistic"))
    expect_equal(as.numeric(engine_row$pValueAdjusted), oracle_row$pValueAdjusted,
      tolerance = irt_tolerance$dif, info = paste0(oracle_row$itemId, ": DIF adjusted p"))
    expect_identical(isTRUE(engine_row$difDetected), isTRUE(oracle_row$difDetected),
      info = paste0(oracle_row$itemId, ": DIF detection"))
  }
  expect_true(isTRUE(engine_dif[["i2"]]$difDetected),
    info = "true-DIF item i2 must be detected")
  expect_false(isTRUE(engine_dif[["i1"]]$difDetected),
    info = "clean item i1 must not be flagged")
})

test_that("GRM item parameters match mirt and recover the generating values", {
  skip_if(is.null(irt_oracle) || !file.exists(file.path(irt_dir, "irt_grm.csv")),
    "IRT golden assets absent")
  items <- read.csv(file.path(irt_dir, "irt_grm.csv"), check.names = FALSE)
  result <- fit_irt_dif_model(
    items, list(list(id = "c", itemIds = paste0("g", seq_len(4)))),
    group_variable = NULL, requested_model = "GRM"
  )
  expect_true(isTRUE(result$available), info = "GRM IRT must be available")
  expect_identical(result$executedIrtModel, "GRM")

  engine_params <- stats::setNames(result$itemParameters,
    vapply(result$itemParameters, `[[`, character(1), "itemId"))
  for (i in seq_along(irt_oracle$mirtGRM)) {
    oracle_row <- irt_oracle$mirtGRM[[i]]
    id <- oracle_row$itemId
    engine_row <- engine_params[[id]]
    expect_equal(as.numeric(engine_row$discrimination), as.numeric(oracle_row$estimate$a),
      tolerance = irt_tolerance$estimate, info = paste0(id, ": a vs mirt"))
    expect_equal(as.numeric(unlist(engine_row$difficulties)), as.numeric(oracle_row$estimate$b),
      tolerance = irt_tolerance$estimate, info = paste0(id, ": thresholds vs mirt"))

    true_a <- irt_oracle$trueGRM$a[[i]]
    true_b <- as.numeric(irt_oracle$trueGRM$b[[i]])
    bound_a <- 3 * as.numeric(oracle_row$standardError$a) + 0.1
    expect_true(abs(as.numeric(oracle_row$estimate$a) - true_a) <= bound_a,
      info = paste0(id, ": recovery of a"))
    for (k in seq_along(true_b)) {
      bound_b <- 3 * as.numeric(oracle_row$standardError$b[[k]]) + 0.1
      expect_true(abs(as.numeric(oracle_row$estimate$b[[k]]) - true_b[[k]]) <= bound_b,
        info = paste0(id, ": recovery of b", k, " (", oracle_row$estimate$b[[k]],
          " vs true ", true_b[[k]], ")"))
    }
  }
})
