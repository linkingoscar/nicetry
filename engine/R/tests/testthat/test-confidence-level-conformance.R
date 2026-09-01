source_engine("lib/runtime.R")
source_engine("lib/seed_utils.R")
source_engine("lib/parallel.R")
source_engine("lib/resource_budget.R")
source_engine("lib/inference_covariance.R")
source_engine("lib/marginal_effects.R")
source_engine("lib/analysis_regression.R")
source_engine("lib/regression_reporting.R")
source_engine("lib/bootstrap.R")
source_engine("lib/factorial_ancova.R")
source_engine("lib/mi_rubin.R")
source_engine("lib/response_surface.R")
source_engine("lib/validity.R")
source_engine("lib/diary_utils.R")
source_engine("lib/diary_bayesian_dsem.R")
source_engine("lib/empirical_group_reporting.R")
source_engine("r_sem_helpers.R")
source_engine("lib/sem_invariance_helpers.R")
assign("w_node", NULL, envir = globalenv())
assign("generic_process", FALSE, envir = globalenv())
assign("template", "", envir = globalenv())
source_engine("lib/moderation_reporting.R")

confidence_levels <- c(0.90, 0.95, 0.99)

interval_widths <- function(rows, lower, upper) {
  vapply(rows, function(row) as.numeric(row[[upper]] - row[[lower]]), numeric(1))
}

expect_increasing_width <- function(widths, label) {
  expect_true(
    all(diff(widths) > 0),
    info = paste(label, paste(format(widths, digits = 8), collapse = ", "))
  )
}

test_that("ordinary OLS and HC3 intervals follow the declared confidence matrix", {
  set.seed(20260819)
  data <- data.frame(
    y = 0.5 + 0.8 * rnorm(180) - 0.3 * rnorm(180) + rnorm(180),
    x = rnorm(180),
    z = rnorm(180)
  )
  fit <- stats::lm(y ~ x + z, data = data)
  hc3 <- researchpath_hc3_covariance(fit)
  expect_true(hc3$available)

  ordinary <- lapply(confidence_levels, function(level) {
    coefficient_rows(fit, identity, confidence_level = level)[[2]]
  })
  robust <- lapply(confidence_levels, function(level) {
    coefficient_rows(
      fit,
      identity,
      robust_se = "HC3",
      confidence_level = level,
      robust_covariance = hc3$covariance
    )[[2]]
  })
  expect_increasing_width(interval_widths(ordinary, "lower", "upper"), "OLS")
  expect_increasing_width(interval_widths(robust, "lower", "upper"), "HC3")
})

test_that("logistic coefficient, OR, AME and ADC intervals follow the declared confidence matrix", {
  set.seed(20260820)
  n <- 360
  data <- data.frame(
    x = rnorm(n),
    treatment = rep(c(0, 1), length.out = n)
  )
  data$y <- stats::rbinom(n, 1, stats::plogis(-0.4 + 0.7 * data$x + 0.45 * data$treatment))
  results <- lapply(confidence_levels, function(level) {
    fit_binary_logistic_with_ame(data, y ~ x + treatment, identity, confidence_level = level)
  })
  x_rows <- lapply(results, function(result) Filter(function(row) identical(row$term, "x"), result$coefficients)[[1]])
  treatment_rows <- lapply(results, function(result) Filter(function(row) identical(row$term, "treatment"), result$coefficients)[[1]])
  expect_equal(vapply(x_rows, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  expect_increasing_width(interval_widths(x_rows, "orCiLower", "orCiUpper"), "logistic OR")
  expect_increasing_width(interval_widths(x_rows, "marginalEffectCiLower", "marginalEffectCiUpper"), "logistic AME")
  expect_increasing_width(interval_widths(treatment_rows, "marginalEffectCiLower", "marginalEffectCiUpper"), "logistic ADC")
})

test_that("PROCESS indirect/conditional bootstrap, J-N and simple-slope intervals use the declared level", {
  assign("replicates", 200L, envir = globalenv())
  assign("bootstrap_config", list(method = "percentile"), envir = globalenv())
  bootstrap_widths <- vapply(confidence_levels, function(level) {
    assign("alpha", 1 - level, envir = globalenv())
    interval <- bootstrap_ci(seq(-0.5, 1.5, length.out = replicates), original_estimate = 0.2)
    interval$upper - interval$lower
  }, numeric(1))
  expect_increasing_width(bootstrap_widths, "PROCESS bootstrap")

  jn <- lapply(confidence_levels, function(level) {
    calc_johnson_neyman(
      b1 = 0.35, b3 = 0.25, var_b1 = 0.02, var_b3 = 0.01,
      cov_b1_b3 = 0.001, df_res = 80, w_min = -2, w_max = 2,
      confidence_level = level
    )
  })
  expect_equal(
    vapply(jn, `[[`, numeric(1), "tCritical"),
    stats::qt(1 - (1 - confidence_levels) / 2, df = 80),
    tolerance = 1e-12
  )

  set.seed(20260821)
  moderation_data <- data.frame(x = rnorm(180), w = rnorm(180))
  moderation_data$y <- 0.4 + 0.5 * moderation_data$x + 0.3 * moderation_data$w +
    0.25 * moderation_data$x * moderation_data$w + rnorm(180)
  fit <<- stats::lm(y ~ x + w + x:w, data = moderation_data)
  covariance <- stats::vcov(fit)
  simple_slope <- lapply(confidence_levels, function(level) {
    build_johnson_neyman(
      b1 = stats::coef(fit)[["x"]], b3 = stats::coef(fit)[["x:w"]],
      covariance = covariance, predictor_term = "x", interaction_term = "x:w",
      moderator_original = moderation_data$w, moderator_center = mean(moderation_data$w),
      critical = stats::qt(1 - (1 - level) / 2, df = stats::df.residual(fit)),
      confidence_level = level, is_glm_fit = FALSE, standard_error_method = "standard"
    )
  })
  expect_equal(vapply(simple_slope, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  simple_slope_widths <- vapply(
    simple_slope,
    function(result) result$grid[[51]]$upper - result$grid[[51]]$lower,
    numeric(1)
  )
  expect_increasing_width(simple_slope_widths, "PROCESS simple slope")
})

test_that("group comparison Tukey and Games-Howell intervals follow declared levels", {
  set.seed(20260824)
  group_data <- data.frame(
    outcome = c(
      rnorm(60, 0, 1),
      rnorm(60, 0.3, 1.1),
      rnorm(60, -0.2, 0.9)
    ),
    group = factor(rep(c("A", "B", "C"), each = 60))
  )
  comparisons <- lapply(confidence_levels, function(level) {
    fit_empirical_group_comparison(
      group_data,
      list(groupVariableId = "group"),
      "outcome",
      function(id) id,
      finite_number,
      FALSE,
      confidence_level = level
    )
  })
  expect_equal(
    vapply(comparisons, function(result) result$results[[1]]$confidenceLevel, numeric(1)),
    confidence_levels
  )
  tukey_widths <- vapply(
    comparisons,
    function(result) {
      row <- result$results[[1]]$pairwiseTukey[[1]]
      row$upper - row$lower
    },
    numeric(1)
  )
  games_howell_widths <- vapply(
    comparisons,
    function(result) {
      row <- result$results[[1]]$pairwiseGamesHowell[[1]]
      row$upper - row$lower
    },
    numeric(1)
  )
  expect_increasing_width(tukey_widths, "group comparison Tukey")
  expect_increasing_width(games_howell_widths, "group comparison Games-Howell")
})

test_that("SEM path and group-difference intervals follow the declared confidence matrix", {
  set.seed(20260824)
  sem_data <- data.frame(x = rnorm(240))
  sem_data$y <- 0.4 + 0.65 * sem_data$x + rnorm(240)
  fit <- lavaan::sem("y ~ x", data = sem_data)
  paths <- lapply(confidence_levels, function(level) {
    get_sem_parameters(fit, confidence_level = level)$paths[[1]]
  })
  expect_increasing_width(interval_widths(paths, "ciLower", "ciUpper"), "SEM path")

  group_parameters <- list(
    list(group = "A", paths = list(list(from = "x", to = "y", estimate = 0.7, standardError = 0.12))),
    list(group = "B", paths = list(list(from = "x", to = "y", estimate = 0.3, standardError = 0.15)))
  )
  differences <- lapply(confidence_levels, function(level) {
    sem_inv_extract_path_comparisons(group_parameters, level)[[1]]
  })
  expect_increasing_width(
    interval_widths(differences, "ciLower", "ciUpper"),
    "SEM group path difference"
  )
})

test_that("experiment EMM and planned contrast intervals follow declared levels", {
  set.seed(20260822)
  experiment <- data.frame(
    y = rnorm(180),
    group = factor(rep(c("A", "B", "C"), each = 60))
  )
  planned <- lapply(confidence_levels, function(level) {
    run_planned_contrasts(experiment, "y", "group", confidence_level = level)
  })
  expect_equal(vapply(planned, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  expect_increasing_width(interval_widths(planned, "ciLower", "ciUpper"), "planned contrast")

  emm <- lapply(confidence_levels, function(level) {
    fit_factorial_ancova(experiment, "y", "group", confidence_level = level)
  })
  expect_equal(vapply(emm, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  emm_rows <- lapply(emm, function(result) result$estimatedMarginalMeans[[1]])
  expect_increasing_width(interval_widths(emm_rows, "ciLower", "ciUpper"), "experiment EMM")
})

test_that("Rubin pooled confidence intervals and HTMT bootstrap intervals follow the declared matrix", {
  pooled <- lapply(confidence_levels, function(level) {
    pool_rubin_estimates(
      estimates = c(0.8, 0.9, 1.1, 1.0),
      standard_errors = c(0.2, 0.21, 0.19, 0.2),
      m_df = c(40, 40, 40, 40),
      confidence_level = level
    )
  })
  expect_equal(vapply(pooled, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  expect_increasing_width(interval_widths(pooled, "ciLower", "ciUpper"), "Rubin")

  items <- data.frame(
    a1 = rnorm(80), a2 = rnorm(80), b1 = rnorm(80), b2 = rnorm(80)
  )
  constructs <- list(
    list(constructId = "a", itemIds = as.list(c("a1", "a2"))),
    list(constructId = "b", itemIds = as.list(c("b1", "b2")))
  )
  htmt <- lapply(confidence_levels, function(level) {
    htmt_bootstrap(items, constructs, reps = 80, seed = 20260823, confidence_level = level)
  })
  expect_equal(vapply(htmt, `[[`, numeric(1), "confidenceLevel"), confidence_levels)
  htmt_widths <- vapply(htmt, function(result) result$upper[[1, 2]] - result$lower[[1, 2]], numeric(1))
  expect_increasing_width(htmt_widths, "HTMT bootstrap")
})

test_that("method-defined Bayesian predictive intervals record their source", {
  result <- dsem_predictive_summary(c(-1, 0, 1), 0, "Y", "mean", predictive = TRUE)
  expect_identical(result$confidenceLevelSource, "method_definition")
})
