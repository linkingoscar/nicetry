source_engine("lib/seed_utils.R")
source_engine("lib/generic_process.R")

test_that("generic bootstrap interval assembly aggregates invalid replicates", {
  values <- matrix(c(0.1, 0.2, 0.3, NA_real_), nrow = 2)
  effect_rows <- list(list(estimate = 0.15), list(estimate = 0.25))
  definitions <- list(list(), list())
  observed <- list()
  interval_function <- function(replicates, original_estimate) {
    observed[[length(observed) + 1L]] <<- list(
      replicates = replicates, original = original_estimate
    )
    list(
      values = c(0.1, 0.2, 0.3),
      lower = 0.1,
      upper = 0.3,
      method = "bootstrap_percentile",
      invalidReplicationCount = if (anyNA(replicates)) 1L else 0L
    )
  }

  result <- researchpath_bootstrap_effect_intervals(
    values, effect_rows, definitions, interval_function,
    confidence_level = 0.95, replicates = 200L, bootstrap_seed = 20260815
  )

  expect_identical(result$invalidReplicationCount, 1L)
  expect_identical(length(observed), 2L)
  expect_true(anyNA(observed[[2]]$replicates))
  expect_identical(result$effects[[1]]$confidenceInterval$replicates, 200L)
  expect_identical(result$effects[[1]]$confidenceInterval$seed, researchpath_seed(20260815))
})
