# Deterministic data-generating cases shared by the independent
# marginaleffects reference generator and its verification test. This file
# contains no product estimator code.

researchpath_logistic_oracle_cases <- function() {
  list(
    list(
      caseId = "A_continuous_x",
      formulaText = "y ~ x",
      method = "avg_slopes",
      targetTerms = "x",
      confidenceLevel = 0.90,
      build = function() {
        set.seed(12345)
        row <- seq_len(240)
        x <- sin(row * 0.13) + cos(row * 0.07)
        eta <- -0.35 + 0.75 * x
        data.frame(y = rbinom(length(row), 1, plogis(eta)), x = x)
      }
    ),
    list(
      caseId = "B_binary_treatment",
      formulaText = "y ~ treatment + x",
      method = "avg_comparisons",
      targetTerms = "treatment",
      confidenceLevel = 0.90,
      build = function() {
        set.seed(12346)
        row <- seq_len(240)
        treatment <- rep(c(0, 1), length.out = length(row))
        x <- cos(row * 0.11) + sin(row * 0.05)
        eta <- -0.60 + 0.95 * treatment + 0.40 * x
        data.frame(y = rbinom(length(row), 1, plogis(eta)), treatment = treatment, x = x)
      }
    ),
    list(
      caseId = "C_three_level_factor",
      formulaText = "y ~ factor3 + x",
      method = "avg_comparisons_reference",
      targetTerms = c("factor3B", "factor3C"),
      confidenceLevel = 0.90,
      build = function() {
        set.seed(12347)
        row <- seq_len(270)
        factor3 <- factor(rep(c("A", "B", "C"), length.out = length(row)), levels = c("A", "B", "C"))
        x <- sin(row * 0.09) - cos(row * 0.04)
        eta <- -0.45 + 0.35 * x + ifelse(factor3 == "B", 0.80, ifelse(factor3 == "C", -0.65, 0))
        data.frame(y = rbinom(length(row), 1, plogis(eta)), factor3 = factor3, x = x)
      }
    ),
    list(
      caseId = "D_low_base_probability",
      formulaText = "y ~ x",
      method = "avg_slopes",
      targetTerms = "x",
      confidenceLevel = 0.90,
      build = function() {
        row <- seq_len(360)
        x <- sin(row * 0.17) + cos(row * 0.03)
        y <- as.integer(row %% 29 == 0)
        data.frame(y = y, x = x)
      }
    ),
    list(
      caseId = "D_high_base_probability",
      formulaText = "y ~ x",
      method = "avg_slopes",
      targetTerms = "x",
      confidenceLevel = 0.90,
      build = function() {
        row <- seq_len(360)
        x <- sin(row * 0.17) + cos(row * 0.03)
        y <- as.integer(row %% 29 != 0)
        data.frame(y = y, x = x)
      }
    )
  )
}

researchpath_logistic_oracle_call <- function(case) {
  data <- case$build()
  fit <- glm(
    stats::as.formula(case$formulaText),
    data = data,
    family = stats::binomial(link = "logit")
  )
  if (identical(case$method, "avg_slopes")) {
    result <- marginaleffects::avg_slopes(
      fit,
      variables = case$targetTerms,
      conf_level = case$confidenceLevel
    )
  } else if (identical(case$method, "avg_comparisons")) {
    result <- marginaleffects::avg_comparisons(
      fit,
      variables = case$targetTerms,
      conf_level = case$confidenceLevel
    )
  } else if (identical(case$method, "avg_comparisons_reference")) {
    result <- marginaleffects::avg_comparisons(
      fit,
      variables = list(factor3 = "reference"),
      conf_level = case$confidenceLevel
    )
  } else {
    stop("Unknown marginaleffects oracle method: ", case$method)
  }
  list(data = data, fit = fit, result = result)
}
