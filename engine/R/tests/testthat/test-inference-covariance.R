source_engine("lib/runtime.R")
source_engine("lib/inference_covariance.R")

test_that("HC3 uses one shared implementation and matches sandwich for OLS", {
  skip_if_not_installed("sandwich")
  set.seed(20260813)
  data <- data.frame(
    y = rnorm(80),
    x = rnorm(80),
    z = rnorm(80)
  )
  fit <- lm(y ~ x + z, data = data)
  result <- researchpath_hc3_covariance(fit)

  expect_true(result$available)
  expect_identical(result$requestedMethod, "HC3")
  expect_identical(result$executedMethod, "HC3")
  expect_false(result$fallbackApplied)
  expect_equal(result$rank, result$parameterCount)
  expect_equal(result$covariance, sandwich::vcovHC(fit, type = "HC3"), tolerance = 1e-10)
})

test_that("HC3 accepts high leverage below one but rejects leverage one", {
  below_one <- lm(c(1, 2, 3, 4) ~ c(-1, 0, 1, 100))
  accepted <- researchpath_hc3_covariance(below_one)
  expect_true(accepted$available)
  expect_lt(accepted$maximumLeverage, 1)

  leverage_one <- lm(c(1, 2, 8) ~ c(0, 0, 1))
  rejected <- researchpath_hc3_covariance(leverage_one)
  expect_false(rejected$available)
  expect_identical(rejected$executedMethod, "not_run")
  expect_false(rejected$fallbackApplied)
  expect_identical(rejected$fallbackReason, "HC3_UNDEFINED_LEVERAGE_ONE")
})

test_that("HC3 rejects rank deficient and near singular designs without classical fallback", {
  data <- data.frame(
    y = seq_len(12),
    x = seq_len(12),
    duplicate = seq_len(12),
    nearly_duplicate = seq_len(12) + seq_len(12) * 1e-14
  )
  rank_deficient <- researchpath_hc3_covariance(lm(y ~ x + duplicate, data = data))
  expect_false(rank_deficient$available)
  expect_identical(rank_deficient$executedMethod, "not_run")
  expect_false(rank_deficient$fallbackApplied)
  expect_identical(rank_deficient$fallbackReason, "HC3_UNDEFINED_RANK_DEFICIENT")

  near_singular <- researchpath_hc3_covariance(lm(y ~ x + nearly_duplicate, data = data))
  expect_false(near_singular$available)
  expect_identical(near_singular$executedMethod, "not_run")
  expect_false(near_singular$fallbackApplied)
  expect_true(near_singular$fallbackReason %in% c(
    "HC3_UNDEFINED_RANK_DEFICIENT",
    "HC3_UNDEFINED_NEAR_SINGULAR",
    "HC3_UNDEFINED_COVARIANCE: system is computationally singular"
  ))
})

test_that("HC3 supports logistic covariance and matches sandwich externally", {
  skip_if_not_installed("sandwich")
  set.seed(20260815)
  n <- 240
  x <- rnorm(n)
  treatment <- rep(c(0, 1), length.out = n)
  probability <- stats::plogis(-0.35 + 0.6 * x + 0.45 * treatment)
  data <- data.frame(
    y = stats::rbinom(n, 1, probability),
    x = x,
    treatment = treatment
  )
  fit <- glm(y ~ x + treatment, data = data, family = binomial())
  result <- researchpath_hc3_covariance(fit)

  expect_true(result$available)
  expect_identical(result$executedMethod, "HC3")
  expect_true(all(is.finite(result$covariance)))
  expect_equal(dim(result$covariance), c(3L, 3L))
  expect_equal(
    result$covariance,
    sandwich::vcovHC(fit, type = "HC3"),
    tolerance = 1e-12
  )
})
