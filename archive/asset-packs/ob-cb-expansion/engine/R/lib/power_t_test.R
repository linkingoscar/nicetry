run_power_t_test <- function(spec, raw_effect, metric, requested_metric, has_effect_size, alpha, target, solve_for) {
  if (!identical(requested_metric, "cohens_d")) stop("POWER_EFFECT_METRIC_NOT_SUPPORTED")
  if (identical(solve_for, "effect_size") && has_effect_size) stop("POWER_EFFECT_SIZE_VALUE_NOT_APPLICABLE")
  if (!identical(solve_for, "effect_size") && !is.null(raw_effect) && !identical(metric, "cohens_d")) stop("T-test power requires Cohen d")
  effect_used <- raw_effect
  groups <- as.integer(spec$groups)
  test_type <- if (identical(groups, 1L)) "one.sample" else "two.sample"
  per_group_n <- function(total_n) if (identical(groups, 1L)) as.numeric(total_n) else as.numeric(total_n) / groups
  test_power <- function(n, effect = effect_used) pwr.t.test(d = effect, n = per_group_n(n), sig.level = alpha, power = NULL, type = test_type, alternative = "two.sided")$power
  analytic <- NULL
  solved <- NULL
  achieved <- NULL
  if (identical(solve_for, "sample_size")) {
    analytic <- pwr.t.test(d = effect_used, n = NULL, sig.level = alpha, power = target, type = test_type, alternative = "two.sided")
    per_group <- ceiling(as.numeric(analytic$n))
    solved <- per_group * groups
    achieved <- test_power(solved)
  } else if (identical(solve_for, "power")) {
    solved <- as.numeric(spec$sampleSize)
    if (groups == 2L && solved %% groups != 0) stop("POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS")
    achieved <- test_power(solved)
  } else {
    solved_n <- as.numeric(spec$sampleSize)
    if (groups == 2L && solved_n %% groups != 0) stop("POWER_SAMPLE_SIZE_NOT_DIVISIBLE_BY_GROUPS")
    analytic <- pwr.t.test(d = NULL, n = per_group_n(solved_n), sig.level = alpha, power = target, type = test_type, alternative = "two.sided")
    upper <- max(1, as.numeric(analytic$d) * 2)
    while (test_power(solved_n, upper) < target) upper <- upper * 2
    effect_used <- uniroot(
      function(value) test_power(solved_n, value) - target,
      interval = c(.Machine$double.eps, upper), tol = 1e-12
    )$root
    solved <- effect_used
    achieved <- test_power(solved_n, effect_used)
  }
  list(
    analytic = analytic,
    solved = solved,
    achieved = achieved,
    effect_used = effect_used,
    power_at = function(n) test_power(n)
  )
}
