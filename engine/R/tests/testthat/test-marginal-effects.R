source_engine("lib/runtime.R")
source_engine("lib/marginal_effects.R")
source_engine("lib/regression_reporting.R")

test_that("raw numeric interactions do not receive an ordinary logistic AME", {
  set.seed(20260815)
  data <- data.frame(
    y = rbinom(200, 1, 0.5),
    x = rnorm(200),
    w = rnorm(200)
  )
  data$xw <- data$x * data$w
  result <- fit_binary_logistic_with_ame(
    data,
    y ~ x + w + x:w,
    identity,
    confidence_level = 0.90
  )
  interaction <- Filter(function(row) row$term == "x:w", result$coefficients)[[1]]

  expect_true(is.na(interaction$averageMarginalEffect))
  expect_identical(interaction$marginalEffectType, "not_applicable_interaction_term")
  expect_identical(interaction$marginalEffectReason, "Use conditional effect or probe output for interaction interpretation.")
  expect_false("marginalEffectConfidenceInterval" %in% names(interaction))
})

test_that("factor interactions do not receive an ordinary logistic AME", {
  set.seed(20260816)
  data <- data.frame(
    y = rbinom(240, 1, 0.5),
    x = rnorm(240),
    group = factor(rep(c("A", "B", "C"), length.out = 240), levels = c("A", "B", "C"))
  )
  result <- fit_binary_logistic_with_ame(
    data,
    y ~ x * group,
    identity,
    confidence_level = 0.99
  )
  interactions <- Filter(function(row) grepl(":", row$term, fixed = TRUE), result$coefficients)

  expect_length(interactions, 2L)
  expect_true(all(vapply(interactions, function(row) {
    is.na(row$averageMarginalEffect) &&
      identical(row$marginalEffectType, "not_applicable_interaction_term") &&
      identical(row$marginalEffectReason, "Use conditional effect or probe output for interaction interpretation.")
  }, logical(1))))
})

test_that("declared product columns do not receive an ordinary model-builder AME", {
  source_engine("lib/inference_covariance.R")
  source_engine("lib/analysis_regression.R")
  set.seed(20260817)
  data <- data.frame(
    y = rbinom(240, 1, 0.5),
    x = rnorm(240),
    w = rnorm(240)
  )
  data$xw <- data$x * data$w
  spec <<- list(
    estimation = list(standardErrors = "classical", confidenceLevel = 0.90),
    moderations = list(list(productTermId = "xw"))
  )
  binary_node_ids <<- character(0)
  fit <- glm(y ~ x + w + xw, data = data, family = binomial())
  rows <- coefficient_rows(fit, "equation_y")
  interaction <- Filter(function(row) row$term == "xw", rows)[[1]]

  expect_true(is.na(interaction$averageMarginalEffect))
  expect_identical(interaction$marginalEffectType, "not_applicable_interaction_term")
  expect_identical(interaction$marginalEffectReason, "Use conditional effect or probe output for interaction interpretation.")
})
