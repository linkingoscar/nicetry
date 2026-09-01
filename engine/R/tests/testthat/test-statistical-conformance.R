source_engine("lib/runtime.R")
source_engine("lib/experimental_cluster_glm.R")
source_engine("lib/sample_adequacy.R")
source_engine("lib/cfa.R")
source_engine("lib/validity.R")
source_engine("lib/esem_bifactor.R")

test_that("cluster GLM two-sided critical values match declared confidence levels", {
  expect_equal(cluster_glm_two_sided_critical(0.90, 7), stats::qt(0.95, 7), tolerance = 1e-12)
  expect_equal(cluster_glm_two_sided_critical(0.95, 7), stats::qt(0.975, 7), tolerance = 1e-12)
  expect_equal(cluster_glm_two_sided_critical(0.99, 7), stats::qt(0.995, 7), tolerance = 1e-12)
})

test_that("two-item reliability uses the standard Spearman-Brown formula", {
  expect_equal(calc_spearman_brown(0.5), 2 * 0.5 / 1.5, tolerance = 1e-12)
  expect_equal(calc_spearman_brown(-0.5), 2 * -0.5 / 0.5, tolerance = 1e-12)
  expect_true(is.na(calc_spearman_brown(-1)))
})

test_that("omega is estimated from a common-factor model rather than PCA", {
  skip_if_not_installed("psych")
  set.seed(20260811)
  latent <- rnorm(500)
  items <- data.frame(
    i1 = 0.85 * latent + rnorm(500, sd = 0.50),
    i2 = 0.70 * latent + rnorm(500, sd = 0.70),
    i3 = 0.55 * latent + rnorm(500, sd = 0.85),
    i4 = 0.40 * latent + rnorm(500, sd = 1.00)
  )
  result <- calc_ordinal_reliability(items, names(items))
  correlation <- cor(items)
  fit <- psych::fa(
    r = correlation,
    nfactors = 1,
    n.obs = nrow(items),
    fm = "minres",
    rotate = "none",
    warnings = FALSE
  )
  loadings <- as.numeric(unclass(fit$loadings)[, 1])
  if (sum(loadings) < 0) loadings <- -loadings
  expected <- sum(loadings)^2 / (sum(loadings)^2 + sum(fit$uniquenesses))
  principal <- eigen(correlation, symmetric = TRUE)
  pca_loadings <- principal$vectors[, 1] * sqrt(principal$values[1])
  if (sum(pca_loadings) < 0) pca_loadings <- -pca_loadings
  old_pca_value <- sum(pca_loadings)^2 / (
    sum(pca_loadings)^2 + sum(1 - pmin(pca_loadings^2, 0.999^2))
  )

  expect_identical(result$method, "one_factor_minres_omega_total")
  expect_equal(result$omega, expected, tolerance = 1e-10)
  expect_gt(abs(result$omega - old_pca_value), 1e-4)
})

test_that("bifactor omega hierarchical uses factor-wise total-score variance", {
  general <- rep(0.5, 4)
  specific <- cbind(
    S_1 = c(0.4, 0.4, 0, 0),
    S_2 = c(0, 0, 0.4, 0.4)
  )
  residual <- rep(0.59, 4)
  result <- bifactor_total_score_metrics(general, specific, residual)
  expected_total <- sum(general)^2 + sum(c(sum(specific[, 1]), sum(specific[, 2]))^2) + sum(residual)

  expect_equal(result$totalScoreVariance, expected_total, tolerance = 1e-12)
  expect_equal(result$omegaHierarchical, 4 / expected_total, tolerance = 1e-12)
  expect_equal(result$omegaHierarchical, 0.523560209424084, tolerance = 1e-12)
  expect_gt(abs(result$omegaHierarchical - 4 / (4 + sum(specific^2) + sum(residual))), 0.04)
  expect_equal(unname(result$specificFactorContributions), c(0.64, 0.64), tolerance = 1e-12)
})

test_that("bifactor score variance preserves loading signs within each specific factor", {
  result <- bifactor_total_score_metrics(
    c(0.5, 0.5),
    cbind(S_1 = c(0.4, -0.4)),
    c(0.59, 0.59)
  )
  expect_equal(result$specificFactorScoreVariance, 0, tolerance = 1e-12)
  expect_error(
    bifactor_total_score_metrics(c(0.5, 0.5), matrix(0.4, nrow = 1), c(0.5, 0.5)),
    "BIFACTOR_SCORE_VARIANCE_DIMENSION_MISMATCH"
  )
})

test_that("ordinal CFA executes WLSMV without a continuous-ML fallback", {
  skip_if_not_installed("lavaan")
  set.seed(20260812)
  latent_a <- rnorm(500)
  latent_b <- 0.30 * latent_a + sqrt(1 - 0.30^2) * rnorm(500)
  discretize <- function(values) as.integer(cut(
    values,
    breaks = c(-Inf, -0.8, -0.2, 0.3, 0.9, Inf),
    labels = FALSE
  ))
  items <- data.frame(
    a1 = discretize(0.85 * latent_a + rnorm(500, sd = 0.55)),
    a2 = discretize(0.75 * latent_a + rnorm(500, sd = 0.65)),
    a3 = discretize(0.70 * latent_a + rnorm(500, sd = 0.70)),
    b1 = discretize(0.85 * latent_b + rnorm(500, sd = 0.55)),
    b2 = discretize(0.75 * latent_b + rnorm(500, sd = 0.65)),
    b3 = discretize(0.70 * latent_b + rnorm(500, sd = 0.70))
  )
  constructs <- list(
    list(id = "a", itemIds = as.list(c("a1", "a2", "a3"))),
    list(id = "b", itemIds = as.list(c("b1", "b2", "b3")))
  )
  result <- fit_cfa(items, constructs, estimator = "WLSMV", ordered_items = names(items))

  expect_true(result$available)
  expect_true(result$converged)
  expect_identical(result$methodExecution$requestedMethod, "lavaan_WLSMV_ordered_simple_structure_CFA")
  expect_identical(result$methodExecution$executedMethod, "lavaan_WLSMV_simple_structure_CFA")
  expect_false(result$methodExecution$fallbackApplied)
})

test_that("mixed-scale empirical CFA is rejected instead of silently using continuous MLR", {
  items <- data.frame(
    a1 = rep(1:5, 24),
    a2 = rep(5:1, 24),
    b1 = seq_len(120) / 10,
    b2 = log(seq_len(120) + 1)
  )
  constructs <- list(
    list(id = "a", itemIds = as.list(c("a1", "a2"))),
    list(id = "b", itemIds = as.list(c("b1", "b2")))
  )
  variable_lookup <- list(
    a1 = list(type = "ordinal"),
    a2 = list(type = "likert"),
    b1 = list(type = "continuous"),
    b2 = list(type = "continuous")
  )
  result <- run_empirical_cfa(items, constructs, names(items), variable_lookup)

  expect_identical(result$itemScale, "mixed")
  expect_false(result$cfa$available)
  expect_identical(
    result$cfa$reason,
    "MIXED_SCALE_CFA_REQUIRES_EXPLICIT_MIXED_CORRELATION_ESTIMATOR"
  )
  expect_identical(result$cfa$methodExecution$requestedMethod, "mixed_item_scales_CFA")
  expect_identical(result$cfa$methodExecution$executedMethod, "not_run")
  expect_false(result$cfa$methodExecution$fallbackApplied)
})

test_that("ordinal HTMT uses the declared polychoric correlation matrix", {
  skip_if_not_installed("lavaan")
  set.seed(20260813)
  latent_a <- rnorm(300)
  latent_b <- 0.35 * latent_a + sqrt(1 - 0.35^2) * rnorm(300)
  ordinal <- function(values) as.integer(cut(
    values,
    breaks = c(-Inf, -0.7, -0.1, 0.4, 1.0, Inf),
    labels = FALSE
  ))
  items <- data.frame(
    a1 = ordinal(0.8 * latent_a + rnorm(300, sd = 0.6)),
    a2 = ordinal(0.7 * latent_a + rnorm(300, sd = 0.7)),
    b1 = ordinal(0.8 * latent_b + rnorm(300, sd = 0.6)),
    b2 = ordinal(0.7 * latent_b + rnorm(300, sd = 0.7))
  )
  constructs <- list(
    list(id = "a", itemIds = as.list(c("a1", "a2"))),
    list(id = "b", itemIds = as.list(c("b1", "b2")))
  )
  polychoric <- abs(unclass(lavaan::lavCor(items, ordered = names(items))))
  expected <- mean(polychoric[c("a1", "a2"), c("b1", "b2")]) /
    sqrt(polychoric["a1", "a2"] * polychoric["b1", "b2"])
  result <- calc_htmt_matrix(items, constructs, correlation_type = "polychoric")

  expect_equal(result[1, 2], expected, tolerance = 1e-10)
  expect_error(
    calc_htmt_matrix(items, constructs, correlation_type = "heterogeneous"),
    "HTMT_UNSUPPORTED_CORRELATION_TYPE"
  )
})
