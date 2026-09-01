# Public-data measurement validation: the empirical EFA path
# (fit_empirical_efa -> stats::factanal) and the empirical CFA path
# (fit_cfa -> fit_lavaan_cfa -> lavaan::cfa MLR) vs direct package calls on
# Holzinger-Swineford 1939.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "public-data-measurement.json")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

measurement_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
measurement_tolerance <- measurement_oracle$provenance$tolerance

source_engine("lib/runtime.R")
source_engine("lib/efa.R")
source_engine("lib/cfa.R")

hs <- lavaan::HolzingerSwineford1939
items9 <- hs[, c("x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9")]

matrix_matches <- function(engine_matrix, oracle_rows, label, tolerance) {
  expect_equal(nrow(engine_matrix), length(oracle_rows), info = paste0(label, ": row count"))
  for (i in seq_along(oracle_rows)) {
    expect_equal(
      as.numeric(engine_matrix[i, ]), as.numeric(oracle_rows[[i]]),
      tolerance = tolerance,
      info = paste0(label, ": row ", i)
    )
  }
}

test_that("empirical EFA (ML varimax/promax) matches stats::factanal on HS1939", {
  skip_if(is.null(measurement_oracle), "measurement oracle absent")
  varimax_result <- fit_empirical_efa(items9, 3, "varimax")
  expect_false(isTRUE(varimax_result$fallbackApplied), info = "EFA varimax must not fall back")
  expect_identical(varimax_result$executedMethod, "maximum_likelihood_factanal_varimax")
  matrix_matches(varimax_result$loadings, measurement_oracle$efa$varimax,
    "EFA varimax", measurement_tolerance$loadings)

  promax_result <- fit_empirical_efa(items9, 3, "promax")
  expect_false(isTRUE(promax_result$fallbackApplied), info = "EFA promax must not fall back")
  matrix_matches(promax_result$loadings, measurement_oracle$efa$promax,
    "EFA promax", measurement_tolerance$loadings)
  matrix_matches(as.matrix(promax_result$factorCorrelations),
    measurement_oracle$efa$promaxFactorCorrelations,
    "EFA promax factor correlations", measurement_tolerance$correlation)
})

test_that("empirical CFA (MLR simple structure) matches lavaan::cfa on HS1939", {
  skip_if(is.null(measurement_oracle), "measurement oracle absent")
  constructs <- list(
    list(id = "visual", itemIds = c("x1", "x2", "x3")),
    list(id = "textual", itemIds = c("x4", "x5", "x6")),
    list(id = "speed", itemIds = c("x7", "x8", "x9"))
  )
  result <- fit_cfa(items9, constructs, estimator = "MLR")
  expect_true(isTRUE(result$available), info = "CFA must be available")
  golden <- measurement_oracle$cfa

  fit_fields <- c(
    "chiSquare", "chiSquareScaled", "degreesOfFreedom", "pValue", "pValueScaled",
    "cfi", "cfiRobust", "tli", "tliRobust", "rmsea", "rmseaRobust", "srmr",
    "rmseaCiLower", "rmseaCiUpper", "rmseaCiLowerRobust", "rmseaCiUpperRobust"
  )
  for (field in fit_fields) {
    expect_equal(
      as.numeric(result[[field]]), golden[[field]],
      tolerance = measurement_tolerance$fit,
      info = paste0("CFA fit ", field)
    )
  }

  expect_equal(
    as.numeric(unlist(result$standardizedLoadings)),
    as.numeric(golden$standardizedLoadings),
    tolerance = measurement_tolerance$loadings,
    info = "CFA standardized loadings (construct order)"
  )

  for (i in seq_along(golden$factorCorrelations)) {
    expect_equal(
      as.numeric(result$factorCorrelations[[i]]),
      as.numeric(golden$factorCorrelations[[i]]),
      tolerance = measurement_tolerance$correlation,
      info = paste0("CFA factor correlation row ", i)
    )
  }

  expect_false(isTRUE(result$hasHeywoodCase), info = "no Heywood case expected")
  expect_false(isTRUE(result$notPositiveDefinite), info = "matrix expected positive definite")
})
