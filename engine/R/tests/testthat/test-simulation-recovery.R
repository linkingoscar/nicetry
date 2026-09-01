source_engine("lib/runtime.R")
source_engine("lib/seed_utils.R")
source_engine("lib/inference_covariance.R")
source_engine("lib/regression_reporting.R")
source_engine("lib/diary_utils.R")
source_engine("lib/diary_bayesian_dsem.R")

validation_manifest <- jsonlite::fromJSON(
  file.path(project_root, "specs", "statistical-validation.json"),
  simplifyVector = FALSE
)

validation_scenario <- function(id) {
  matches <- Filter(function(item) identical(item$id, id), validation_manifest$scenarios)
  if (length(matches) != 1L) stop("VALIDATION_SCENARIO_NOT_UNIQUE: ", id)
  matches[[1]]
}

expect_metric_threshold <- function(value, threshold, label) {
  if (!is.null(threshold$minimum)) {
    expect_true(value >= as.numeric(threshold$minimum), info = label)
  }
  if (!is.null(threshold$maximum)) {
    expect_true(value <= as.numeric(threshold$maximum), info = label)
  }
}

test_that("cross-sectional OLS recovers bias coverage type-I power and independent oracle", {
  scenario <- validation_scenario("cross-sectional-ols-recovery-v1")
  repetitions <- as.integer(scenario$repetitions)
  set.seed(as.integer(scenario$seed))
  estimates <- coverage <- null_rejections <- power_rejections <- finite_runs <- numeric(repetitions)
  oracle_differences <- numeric(repetitions)
  true_beta <- 0.50
  for (replicate_index in seq_len(repetitions)) {
    n <- 120L
    x <- rnorm(n)
    z <- rnorm(n)
    error <- rnorm(n)
    data <- data.frame(
      y = 0.2 + true_beta * x - 0.25 * z + error,
      y_null = 0.2 - 0.25 * z + error,
      x = x,
      z = z
    )
    fit <- lm(y ~ x + z, data = data)
    rows <- coefficient_rows(fit, identity, confidence_level = 0.95)
    x_row <- Filter(function(row) identical(row$term, "x"), rows)[[1]]
    null_fit <- lm(y_null ~ x + z, data = data)
    null_row <- Filter(
      function(row) identical(row$term, "x"),
      coefficient_rows(null_fit, identity, confidence_level = 0.95)
    )[[1]]

    # Independent closed-form implementation: no lm(), summary.lm(), or
    # coefficient_rows() is used for the oracle quantities.
    design <- cbind(1, x, z)
    inverse_information <- solve(crossprod(design))
    oracle_beta <- drop(inverse_information %*% crossprod(design, data$y))
    oracle_residual <- data$y - drop(design %*% oracle_beta)
    oracle_sigma2 <- sum(oracle_residual^2) / (n - ncol(design))
    oracle_se <- sqrt(diag(oracle_sigma2 * inverse_information))
    oracle_differences[[replicate_index]] <- max(
      abs(x_row$estimate - oracle_beta[[2]]),
      abs(x_row$standardError - oracle_se[[2]])
    )
    estimates[[replicate_index]] <- x_row$estimate
    coverage[[replicate_index]] <- x_row$lower <= true_beta && x_row$upper >= true_beta
    null_rejections[[replicate_index]] <- null_row$pValue < 0.05
    power_rejections[[replicate_index]] <- x_row$pValue < 0.05
    finite_runs[[replicate_index]] <- all(is.finite(c(
      x_row$estimate, x_row$standardError, x_row$pValue, x_row$lower, x_row$upper
    )))
  }
  coverage_rate <- mean(coverage)
  type_i_rate <- mean(null_rejections)
  metrics <- list(
    absoluteBias = abs(mean(estimates) - true_beta),
    coverage95 = coverage_rate,
    typeIError = type_i_rate,
    power = mean(power_rejections),
    finiteRunRate = mean(finite_runs),
    coverageMcse = sqrt(coverage_rate * (1 - coverage_rate) / repetitions),
    typeIMcse = sqrt(type_i_rate * (1 - type_i_rate) / repetitions),
    oracleMaxDifference = max(oracle_differences)
  )
  for (name in names(metrics)) {
    expect_metric_threshold(metrics[[name]], scenario$thresholds[[name]], name)
  }
})

dsem_calibration_groups <- function(beta, seed) {
  set.seed(seed)
  lapply(seq_len(10L), function(group_index) {
    n <- 24L
    own_lag <- rnorm(n)
    cross_lag <- rnorm(n)
    design <- cbind(1, own_lag, cross_lag)
    random_intercept <- rnorm(1L, sd = 0.30)
    list(
      y = drop(design %*% beta + random_intercept + rnorm(n, sd = 0.70)),
      x = design,
      z = matrix(1, nrow = n, ncol = 1L)
    )
  })
}

test_that("DSEM SBC ranks and posterior predictive checks stay calibrated as internal smoke", {
  scenario <- validation_scenario("dsem-sbc-ppc-smoke-v1")
  repetitions <- as.integer(scenario$repetitions)
  ranks <- numeric(repetitions)
  predictive_p <- numeric(0)
  finite_draws <- numeric(repetitions)
  for (replicate_index in seq_len(repetitions)) {
    truth_seed <- researchpath_seed(scenario$seed, replicate_index * 1009L)
    set.seed(truth_seed)
    beta <- c(rnorm(1L, 0, 0.25), rnorm(1L, 0.35, 0.08), rnorm(1L, 0.20, 0.08))
    groups <- dsem_calibration_groups(beta, researchpath_seed(truth_seed, 17L))
    settings <- list(
      iterations = 500L,
      warmup = 250L,
      thin = 1L,
      priorScale = 1,
      priorMeanSd = 2,
      predictiveReplications = 80L,
      seed = researchpath_seed(truth_seed, 29L)
    )
    chain <- dsem_gibbs_equation(groups, settings, researchpath_seed(truth_seed, 41L))
    cross_lag_draws <- chain$beta[, 3]
    ranks[[replicate_index]] <- mean(cross_lag_draws < beta[[3]])
    finite_draws[[replicate_index]] <- mean(is.finite(c(
      chain$beta, chain$randomSd, chain$residualVariance
    )))
    checks <- dsem_posterior_predictive_checks(
      groups,
      list(chain),
      settings,
      "Y",
      replicate_index * 7919L
    )
    predictive_p <- c(
      predictive_p,
      vapply(checks, `[[`, numeric(1), "bayesianPValue")
    )
  }
  metrics <- list(
    sbcRankMean = mean(ranks),
    ppcCentralRate = mean(predictive_p >= 0.025 & predictive_p <= 0.975),
    finiteDrawRate = mean(finite_draws)
  )
  for (name in names(metrics)) {
    expect_metric_threshold(metrics[[name]], scenario$thresholds[[name]], name)
  }
  expect_identical(scenario$oracle$validationClaim, "internal")
})
