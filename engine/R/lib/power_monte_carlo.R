run_power_monte_carlo <- function() {
  if (!identical(spec$designFamily, "regression") && !identical(spec$designFamily, "factorial_anova")) {
    stop("POWER_MONTE_CARLO_NOT_SUPPORTED")
  }
  if (is.null(spec$monteCarloParameters)) stop("POWER_MONTE_CARLO_PARAMETERS_REQUIRED")
  confidence_level <- researchpath_validate_confidence_level(spec$confidenceLevel)
  simulations <- as.integer(spec$simulations)
  alpha <- as.numeric(spec$alpha)
  target <- as.numeric(spec$targetPower)
  solve_for <- spec$solveFor
  design <- spec$designFamily
  metric <- if (identical(solve_for, "effect_size")) spec$effectSizeMetric else spec$effectSize$metric
  raw_effect <- if (is.null(spec$effectSize)) NULL else as.numeric(spec$effectSize$value)
  if (is.null(metric)) stop("POWER_EFFECT_METRIC_REQUIRED")
  estimated_evaluations <- if (identical(solve_for, "sample_size")) 32L else if (identical(solve_for, "effect_size")) 22L else 7L
  researchpath_budget_power_monte_carlo(
    simulations,
    if (identical(design, "regression")) as.integer(spec$predictors) else as.integer(spec$groups),
    estimated_evaluations
  )
  dgp <- spec$monteCarloParameters$dataGeneration
  failure_handling <- if (is.null(spec$monteCarloParameters$convergenceFailureHandling)) "drop" else spec$monteCarloParameters$convergenceFailureHandling
  error_sd <- if (!is.null(dgp$errorSd)) as.numeric(dgp$errorSd) else 1
  if (!is.finite(error_sd) || error_sd <= 0) stop("POWER_MONTE_CARLO_DGP_INVALID")

  wilson_interval <- function(successes, valid) {
    z <- stats::qnorm(1 - (1 - confidence_level) / 2)
    p <- successes / valid
    denominator <- 1 + z^2 / valid
    center <- (p + z^2 / (2 * valid)) / denominator
    half <- z * sqrt(p * (1 - p) / valid + z^2 / (4 * valid^2)) / denominator
    c(max(0, center - half), min(1, center + half))
  }
  as_f2 <- function(effect) {
    if (identical(metric, "r_squared_change")) effect / (1 - effect) else effect
  }
  simulate_power <- function(sample_size, effect) {
    sample_size <- as.integer(sample_size)
    successes <- 0L
    failures <- 0L
    for (replicate in seq_len(simulations)) {
      if (replicate %% 25L == 0L) {
        write_progress("power_monte_carlo", replicate / simulations, replicate, simulations)
        check_cancel()
      }
      p_value <- tryCatch({
        if (identical(design, "regression")) {
          predictors <- as.integer(spec$predictors)
          correlation <- if (!is.null(dgp$predictorCorrelation)) as.numeric(dgp$predictorCorrelation) else 0
          if (abs(correlation) >= 1) stop("invalid predictor correlation")
          covariance <- matrix(correlation, predictors, predictors)
          diag(covariance) <- 1
          if (any(eigen(covariance, symmetric = TRUE, only.values = TRUE)$values <= 0)) stop("non-positive predictor covariance")
          x <- matrix(stats::rnorm(sample_size * predictors), nrow = sample_size, ncol = predictors) %*% chol(covariance)
          raw_beta <- rep(1, predictors)
          linear_signal <- drop(x %*% raw_beta)
          signal_sd <- stats::sd(linear_signal)
          beta <- raw_beta * sqrt(as_f2(effect) * error_sd^2) / max(signal_sd, .Machine$double.eps)
          outcome <- drop(x %*% beta) + stats::rnorm(sample_size, sd = error_sd)
          fit <- stats::lm(outcome ~ x)
          f_stat <- summary(fit)$fstatistic
          if (is.null(f_stat) || !is.finite(f_stat[[1]])) stop("regression F statistic unavailable")
          stats::pf(f_stat[[1]], f_stat[[2]], f_stat[[3]], lower.tail = FALSE)
        } else {
          groups <- as.integer(spec$groups)
          per_group <- sample_size / groups
          if (per_group != floor(per_group)) stop("sample size is not divisible by groups")
          group <- factor(rep(seq_len(groups), each = per_group))
          means <- if (!is.null(dgp$groupMeans)) as.numeric(unlist(dgp$groupMeans, use.names = FALSE)) else seq(-1, 1, length.out = groups)
          if (length(means) != groups) stop("groupMeans length mismatch")
          means <- means - mean(means)
          mean_sd <- sqrt(mean(means^2))
          means <- means * as.numeric(effect) / max(mean_sd, .Machine$double.eps) * error_sd
          outcome <- means[as.integer(group)] + stats::rnorm(sample_size, sd = error_sd)
          fit <- stats::aov(outcome ~ group)
          anova_table <- summary(fit)[[1]]
          anova_table[[1, ncol(anova_table)]]
        }
      }, error = function(error) NULL)
      if (is.null(p_value) || !is.finite(p_value)) failures <- failures + 1L else if (p_value < alpha) successes <- successes + 1L
    }
    valid <- simulations - failures
    if (identical(failure_handling, "fail") && failures > 0L) stop("POWER_MONTE_CARLO_CONVERGENCE_FAILURE")
    if (valid < max(100L, ceiling(simulations * 0.8))) stop("POWER_MONTE_CARLO_TOO_MANY_FAILURES")
    probability <- successes / valid
    list(
      power = probability,
      mcse = sqrt(probability * (1 - probability) / valid),
      valid = valid,
      failures = failures,
      confidenceInterval = wilson_interval(successes, valid)
    )
  }

  evaluate_target <- function(sample_size, effect) simulate_power(sample_size, effect)
  if (identical(solve_for, "power")) {
    solved <- as.numeric(spec$sampleSize)
    effect_used <- raw_effect
    final <- evaluate_target(solved, effect_used)
  } else if (identical(solve_for, "sample_size")) {
    effect_used <- raw_effect
    lower <- if (identical(design, "regression")) as.integer(spec$predictors) + 2L else as.integer(spec$groups) * 2L
    upper <- max(lower * 2L, 20L)
    while (evaluate_target(upper, effect_used)$power < target && upper < 20000L) upper <- upper * 2L
    if (evaluate_target(upper, effect_used)$power < target) stop("POWER_MONTE_CARLO_TARGET_UNREACHABLE")
    for (iteration in seq_len(12L)) {
      midpoint <- if (identical(design, "factorial_anova")) as.integer(ceiling(((lower + upper) / 2) / spec$groups) * spec$groups) else as.integer(ceiling((lower + upper) / 2))
      if (evaluate_target(midpoint, effect_used)$power >= target) upper <- midpoint else lower <- midpoint + if (identical(design, "factorial_anova")) spec$groups else 1L
    }
    solved <- upper
    final <- evaluate_target(solved, effect_used)
  } else {
    solved_sample_size <- as.numeric(spec$sampleSize)
    lower <- .0001
    upper <- if (identical(metric, "r_squared_change")) .99 else 2
    if (evaluate_target(solved_sample_size, upper)$power < target) {
      if (identical(metric, "r_squared_change")) stop("POWER_MONTE_CARLO_TARGET_UNREACHABLE")
      while (evaluate_target(solved_sample_size, upper)$power < target && upper < 100) upper <- upper * 2
      if (evaluate_target(solved_sample_size, upper)$power < target) stop("POWER_MONTE_CARLO_TARGET_UNREACHABLE")
    }
    for (iteration in seq_len(14L)) {
      midpoint <- (lower + upper) / 2
      if (evaluate_target(solved_sample_size, midpoint)$power >= target) upper <- midpoint else lower <- midpoint
    }
    solved <- if (identical(metric, "r_squared_change")) min(upper, .99) else upper
    effect_used <- solved
    final <- evaluate_target(solved_sample_size, effect_used)
  }
  curve_base <- if (identical(solve_for, "sample_size")) solved else as.numeric(spec$sampleSize)
  if (identical(design, "regression")) curve_n <- unique(pmax(as.integer(spec$predictors) + 2L, round(curve_base * c(.8, .9, 1, 1.1, 1.2)))) else curve_n <- unique(as.integer(spec$groups) * pmax(2L, round(curve_base * c(.8, .9, 1, 1.1, 1.2) / spec$groups)))
  curve <- lapply(curve_n, function(n) {
    point <- evaluate_target(n, effect_used)
    list(sampleSize = as.integer(n), power = finite(point$power), monteCarloStandardError = finite(point$mcse))
  })
  reported_effect <- if (identical(solve_for, "effect_size")) solved else raw_effect
  warnings <- list(message_entry("POWER_MONTE_CARLO_SAMPLING_ERROR", "warning", "Monte Carlo power is an estimate; interpret it with the reported MCSE and confidence interval."))
  if (final$failures > 0L) {
    warnings[[length(warnings) + 1L]] <- message_entry(
      "POWER_MONTE_CARLO_CONVERGENCE_FAILURES",
      "warning",
      sprintf("%s of %s Monte Carlo replicates failed. Power is calculated from %s valid replicates; inspect the declared DGP and model stability.", final$failures, simulations, final$valid)
    )
  }
  list(
    sampleFlow = list(original = 0L, included = 0L, excluded = 0L, missingMethod = "not applicable"),
    estimates = list(estimate_entry("power", "Monte Carlo achieved power", final$power, se = final$mcse, scale = "probability")),
    diagnostics = list(message_entry("POWER_MONTE_CARLO_COMPLETED", "info", sprintf("Completed %s valid Monte Carlo replicates with %s convergence failures", final$valid, final$failures))),
    warnings = warnings,
    provenance = list(engine = "ResearchPath R Monte Carlo power engine", engineVersion = "0.1.0", softwareVersions = list(R = as.character(getRversion())), estimand = "frequentist rejection probability under declared DGP", degreesOfFreedomMethod = "model-specific Monte Carlo test", sliceId = "power_analysis.monte_carlo"),
    familyResult = list(
      family = family,
      solveFor = solve_for,
      solvedValue = as.numeric(solved),
      achievedPower = as.numeric(final$power),
      monteCarloStandardError = as.numeric(final$mcse),
      powerCurve = curve,
      method = "monte_carlo",
      confidenceLevel = confidence_level,
      simulationCount = simulations,
      validSimulations = final$valid,
      failureCount = final$failures,
      confidenceInterval = as.list(final$confidenceInterval),
      parameters = list(
        alpha = alpha,
        alternative = "two_sided",
        groups = as.integer(spec$groups),
        predictors = as.integer(spec$predictors),
        effectSize = if (is.null(spec$effectSize)) NULL else spec$effectSize,
        effectSizeMetric = metric,
        solvedValueMetric = if (identical(solve_for, "sample_size")) "total_sample_size" else if (identical(solve_for, "power")) "power" else metric,
        solvedEffectSize = if (identical(solve_for, "effect_size")) list(metric = metric, value = as.numeric(solved)) else NULL,
        allocationRatio = NULL
      )
    ),
    apaReports = list(sprintf("A Monte Carlo power analysis used %s valid simulations (MCSE = %.4f) under the declared %s data-generating process.", final$valid, final$mcse, design))
  )
}
