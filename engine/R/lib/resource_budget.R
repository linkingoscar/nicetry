researchpath_require_budget <- function(value, maximum, label) {
  value <- as.double(value)
  maximum <- as.double(maximum)
  if (!is.finite(value) || value < 0 || value > maximum) {
    stop(sprintf("%s exceeds resource budget (%s > %s)", label, format(value, scientific = FALSE), format(maximum, scientific = FALSE)))
  }
  invisible(value)
}

researchpath_budget_parallel_analysis <- function(n, p, iterations) {
  researchpath_require_budget(as.double(iterations) * as.double(n) * as.double(p)^2, 5e8, "parallel analysis work")
  researchpath_require_budget(as.double(iterations) * as.double(p), 2e6, "parallel analysis result allocation")
}

researchpath_budget_htmt <- function(n, p, constructs, replicates) {
  researchpath_require_budget(as.double(replicates) * as.double(constructs)^2, 2e6, "HTMT bootstrap allocation")
  researchpath_require_budget(as.double(replicates) * as.double(n) * as.double(max(1L, p))^2, 5e8, "HTMT bootstrap work")
}

researchpath_budget_custom_cfa <- function(items, constructs) {
  parameters <- 2 * as.double(items) + as.double(constructs) * as.double(max(0L, constructs - 1L)) / 2
  researchpath_require_budget(items, 80, "custom CFA item count")
  researchpath_require_budget(parameters, 5000, "custom CFA parameter count")
}

researchpath_budget_sem <- function(n, variables, replicates, fit_multiplier) {
  work <- as.double(n) * as.double(max(1L, variables))^2 * as.double(max(1L, replicates)) * as.double(max(1L, fit_multiplier))
  researchpath_require_budget(work, 1e9, "SEM bootstrap and invariance work")
}

researchpath_budget_power_monte_carlo <- function(simulations, predictors, estimated_evaluations) {
  # Power simulations retain only running counts, not replicate-level data. The
  # allocation guard therefore controls random-design size; the work guard
  # controls the number of model fits, including sample-size/effect searches.
  researchpath_require_budget(
    as.double(simulations) * as.double(max(1L, predictors)),
    2e6,
    "Monte Carlo random-design allocation"
  )
  researchpath_require_budget(
    as.double(simulations) * as.double(max(1L, estimated_evaluations)),
    4e6,
    "Monte Carlo simulation work"
  )
}

researchpath_budget_mice <- function(rows, variables, imputations, iterations) {
  allocation <- as.double(rows) * as.double(variables) * as.double(imputations)
  work <- allocation * as.double(iterations)
  if (!is.finite(allocation) || allocation > 2e6 || !is.finite(work) || work > 5e8) {
    stop("MI_RESOURCE_BUDGET_EXCEEDED", call. = FALSE)
  }
  invisible(list(allocation = allocation, work = work))
}
