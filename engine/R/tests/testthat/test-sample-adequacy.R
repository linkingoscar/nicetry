source_engine("lib/runtime.R")
source_engine("lib/sample_adequacy.R")

test_that("small CFA samples remain computable but are not confirmatory", {
  items <- as.data.frame(matrix(rnorm(24 * 12), nrow = 24, ncol = 12))
  constructs <- lapply(seq_len(3), function(index) list(id = paste0("c", index)))
  cfa <- list(
    available = TRUE,
    converged = TRUE,
    estimatedParameterCount = 27L
  )

  result <- assess_measurement_sample_adequacy(items, constructs, cfa)

  expect_false(result$passes)
  expect_identical(result$evidence$status, "caution")
  expect_equal(result$evidence$completeCases, 24L)
  expect_equal(result$evidence$casesPerParameter, 24 / 27)
  expect_false(result$cfa$validForConfirmatoryInterpretation)
  expect_match(result$evidence$ruleNature, "not a universal")
})

test_that("adequate fitted samples retain explicit guardrail evidence", {
  items <- as.data.frame(matrix(rnorm(300 * 8), nrow = 300, ncol = 8))
  constructs <- lapply(seq_len(2), function(index) list(id = paste0("c", index)))
  cfa <- list(
    available = TRUE,
    converged = TRUE,
    estimatedParameterCount = 40L
  )

  result <- assess_measurement_sample_adequacy(items, constructs, cfa)

  expect_true(result$passes)
  expect_identical(result$evidence$status, "adequate")
  expect_true(result$cfa$validForConfirmatoryInterpretation)
  expect_identical(
    result$evidence$parameterCountSource,
    "fitted model free-parameter count"
  )
})
