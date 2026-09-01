# Synthetic truth tests (§11C): recover KNOWN factor structures from data
# generated with a fixed seed, and use a pinned reference implementation
# (psych::fa, fixed version) as a difference detector. The goal is structure
# recovery within tolerance plus fixed-seed reproducibility, not bit-for-bit
# agreement.

source_engine("lib/runtime.R")
source_engine("lib/seed_utils.R")
source_engine("lib/parallel.R")
source_engine("lib/resource_budget.R")
source_engine("lib/efa.R")

Sys.setenv(RESEARCHPATH_PARALLEL_WORKERS = "1")

# Pin the difference detector: renv.lock fixes psych at 2.6.5. If the installed
# reference moves, the tolerance comparison below must be revalidated.
test_that("psych difference detector runs at the pinned version", {
  skip_if_not_installed("psych")
  expect_identical(
    as.character(packageVersion("psych")),
    "2.6.5"
  )
})

synthetic_one_factor <- local({
  set.seed(20260807)
  latent <- rnorm(300)
  data <- as.data.frame(lapply(1:8, function(i) 0.7 * latent + rnorm(300, sd = 0.6)))
  names(data) <- paste0("item", 1:8)
  data
})

synthetic_three_factor <- local({
  set.seed(20260807)
  f1 <- rnorm(400)
  f2 <- rnorm(400)
  f3 <- rnorm(400)
  data <- as.data.frame(c(
    lapply(1:5, function(i) 0.7 * f1 + rnorm(400, sd = 0.6)),
    lapply(1:5, function(i) 0.7 * f2 + rnorm(400, sd = 0.6)),
    lapply(1:5, function(i) 0.7 * f3 + rnorm(400, sd = 0.6))
  ))
  names(data) <- paste0("item", 1:15)
  data
})

# Ordinal items generated from one latent with skewed category thresholds
# (most respondents agree), the hardest case for naive Pearson-based PA.
synthetic_ordinal_skew <- local({
  set.seed(20260807)
  latent <- rnorm(400)
  data <- as.data.frame(lapply(1:8, function(i) {
    z <- 0.75 * latent + rnorm(400, sd = 0.7)
    as.numeric(findInterval(z, c(-2.0, -0.9, 0.2, 1.3)) + 1L)
  }))
  names(data) <- paste0("item", 1:8)
  data
})

test_that("known one-factor continuous structure is recovered", {
  result <- run_parallel_analysis(synthetic_one_factor, iterations = 80, seed = 11)
  expect_true(result$available)
  expect_identical(result$recommendedFactorCount, 1L)
})

test_that("known three-factor continuous structure is recovered", {
  result <- run_parallel_analysis(synthetic_three_factor, iterations = 80, seed = 22)
  expect_true(result$available)
  expect_identical(result$recommendedFactorCount, 3L)
})

test_that("noise-only data may yield a zero-factor parallel-analysis recommendation", {
  set.seed(1)
  noise <- as.data.frame(matrix(rnorm(500 * 8), nrow = 500, ncol = 8))
  names(noise) <- paste0("noise", seq_len(ncol(noise)))

  result <- run_parallel_analysis(noise, iterations = 80, seed = 1001)

  expect_true(result$available)
  expect_identical(result$recommendedFactorCount, 0L)
  expect_identical(result$reason, "no_factor_exceeds_parallel_threshold")
})

test_that("known one-factor ordinal skew structure is recovered in the polychoric world", {
  result <- run_parallel_analysis(
    synthetic_ordinal_skew, iterations = 80, seed = 33,
    correlation_type = "polychoric"
  )
  expect_true(result$available)
  expect_identical(result$correlationType, "polychoric")
  expect_identical(result$recommendedFactorCount, 1L)

  # The fixture really is skewed: the least frequent category is a small
  # fraction of the sample, so a Gaussian null would be a poor approximation.
  marginals <- table(synthetic_ordinal_skew[[1]])
  expect_lt(min(marginals) / sum(marginals), 0.1)
})

test_that("fixed seed reproduces the null eigenvalue distribution", {
  for (correlation_type in c("pearson", "polychoric")) {
    first <- run_parallel_analysis(
      if (identical(correlation_type, "polychoric")) synthetic_ordinal_skew else synthetic_three_factor,
      iterations = 60,
      seed = 271828,
      correlation_type = correlation_type
    )
    second <- run_parallel_analysis(
      if (identical(correlation_type, "polychoric")) synthetic_ordinal_skew else synthetic_three_factor,
      iterations = 60,
      seed = 271828,
      correlation_type = correlation_type
    )
    expect_true(first$available)
    expect_identical(first$simulatedEigenvalues, second$simulatedEigenvalues)
    expect_identical(first$sampleEigenvalues, second$sampleEigenvalues)
  }
})

test_that("ML loadings agree with pinned psych::fa as difference detector", {
  skip_if_not_installed("psych")
  correlation <- cor(synthetic_three_factor)

  ours <- stats::factanal(covmat = correlation, factors = 3, n.obs = 400, rotation = "none")
  reference <- psych::fa(r = correlation, nfactors = 3, n.obs = 400, fm = "ml", rotate = "none")
  ours_loadings <- unclass(ours$loadings)
  reference_loadings <- unclass(reference$loadings)
  for (j in seq_len(3)) {
    if (sum(ours_loadings[, j] * reference_loadings[, j]) < 0) {
      reference_loadings[, j] <- -reference_loadings[, j]
    }
  }
  expect_lt(max(abs(ours_loadings - reference_loadings)), 1e-3)

  # Rotation-invariant cross-check on the product's promax path.
  ours_promax <- run_efa_with_method(
    data = synthetic_three_factor,
    correlation = correlation,
    n_obs = 400,
    factor_count = 3,
    method = "ml",
    rotation = "promax",
    item_scale = "continuous"
  )
  reference_promax <- psych::fa(r = correlation, nfactors = 3, n.obs = 400, fm = "ml", rotate = "promax")
  communalities_ours <- pmin(rowSums(ours_promax$loadings^2), 1)
  communalities_ref <- pmin(rowSums(unclass(reference_promax$loadings)^2), 1)
  expect_lt(max(abs(communalities_ours - communalities_ref)), 1e-3)
})
