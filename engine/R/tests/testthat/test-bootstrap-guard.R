# Bootstrap replication-loss guards: the ≤5% budget drops invalid
# replications with a visible warning upstream; beyond 5% the engine refuses
# to report intervals and raises a coded error instead of a bare message.

source_engine("lib/bootstrap.R")

local({
  replicates <<- 1000L
  alpha <<- 0.05
  bootstrap_config <<- list(method = "percentile")
})

test_that("bootstrap_ci drops invalid replications within the 5% budget", {
  values <- c(rnorm(960, 0.5, 0.1), rep(NA_real_, 40))
  result <- bootstrap_ci(values, 0.5)
  expect_identical(result$invalidReplicationCount, 40L)
  expect_length(result$values, 960)
  expect_identical(result$method, "bootstrap_percentile")
  expect_true(result$lower <= result$upper)
})

test_that("bootstrap_ci keeps the interval when invalid count is exactly at the boundary", {
  # floor(1000 * 0.95) = 950 valid is the minimum accepted.
  values <- c(rnorm(950, 0.5, 0.1), rep(NA_real_, 50))
  result <- bootstrap_ci(values, 0.5)
  expect_identical(result$invalidReplicationCount, 50L)
})

test_that("bootstrap_ci raises a coded error above the 5% budget", {
  values <- c(rnorm(940, 0.5, 0.1), rep(NA_real_, 60))
  expect_error(
    bootstrap_ci(values, 0.5),
    "BOOTSTRAP_REPLICATION_LOSS_EXCEEDS_LIMIT"
  )
})

test_that("bootstrap_ci bias-corrected branch reports dropped count too", {
  bootstrap_config <<- list(method = "bias_corrected")
  values <- c(rnorm(970, 0.5, 0.1), rep(NaN, 30))
  result <- bootstrap_ci(values, 0.5)
  expect_identical(result$invalidReplicationCount, 30L)
  expect_identical(result$method, "bootstrap_bias_corrected")
  bootstrap_config <<- list(method = "percentile")
})
