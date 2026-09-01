source_engine("lib/efa.R")
source_engine("lib/cfa_validity.R")

measurement_fixture <- local({
  set.seed(20260729)
  latent_a <- rnorm(80)
  latent_b <- rnorm(80)
  data.frame(
    item_1 = 0.8 * latent_a + rnorm(80, sd = 0.5),
    item_2 = 0.7 * latent_a + rnorm(80, sd = 0.6),
    item_3 = 0.8 * latent_b + rnorm(80, sd = 0.5),
    item_4 = 0.7 * latent_b + rnorm(80, sd = 0.6)
  )
})

test_that("factanal failure is recorded as an explicit PCA fallback", {
  forced_failure <- function(...) stop("forced factanal failure")

  result <- fit_empirical_efa(
    measurement_fixture,
    factor_count = 2,
    rotation = "varimax",
    factanal_runner = forced_failure
  )

  expect_true(result$fallbackApplied)
  expect_identical(result$fallbackCode, "EFA_FACTANAL_FALLBACK_PCA")
  expect_match(result$fallbackReason, "forced factanal failure")
  expect_identical(result$requestedMethod, "maximum_likelihood_factanal_varimax")
  expect_identical(result$executedMethod, "principal_components_varimax")
  expect_match(result$interpretationBoundary, "不是共同因子模型")
  expect_equal(dim(result$loadings), c(4L, 2L))
  expect_equal(
    unname(colSums(result$loadings^2)),
    c(1.7421, 1.6178),
    tolerance = 1e-4
  )
})

test_that("single-factor eigen fallback has a stable numeric contract", {
  result <- single_factor_eigen_loadings(measurement_fixture[, c("item_1", "item_2")])

  expect_named(result, c("item_1", "item_2"))
  expect_equal(
    unname(result),
    c(0.9345, 0.9345),
    tolerance = 1e-4
  )
})
