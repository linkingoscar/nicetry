args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_foundation_reference.R <case-dir> <output.json>")

suppressPackageStartupMessages(library(jsonlite))
case_dir <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
manifest <- yaml::read_yaml(file.path(case_dir, "manifest.yaml"))
spec <- jsonlite::fromJSON(file.path(case_dir, manifest$specPath), simplifyVector = FALSE)
data <- utils::read.csv(file.path(case_dir, "data", "input.csv"), check.names = FALSE,
  stringsAsFactors = FALSE)
capability <- manifest$identity$capabilityId

failure <- function(reason_code, message) list(
  status = "failed",
  failure = list(reasonCode = reason_code, message = message,
    mustNotReturnEstimates = TRUE, mustNotFallback = TRUE)
)

rubin_reference <- function(q, u, complete_df = NULL) {
  if (length(q) < 2L) return(failure("RUBIN_TOO_FEW_IMPUTATIONS", "Rubin pooling requires at least two imputations"))
  if (length(u) != length(q) || any(!is.finite(q)) || any(!is.finite(u)) || any(u <= 0)) {
    return(failure("RUBIN_INVALID_WITHIN_VARIANCE", "Estimates and within variances must be finite, with positive variance"))
  }
  if (!requireNamespace("mice", quietly = TRUE)) stop("mice is required for the primary Rubin reference")
  n_value <- if (is.null(complete_df)) Inf else as.numeric(complete_df) + 1
  pooled <- mice::pool.scalar(Q = q, U = u, n = n_value, k = 1L)
  list(
    pooled_estimate = as.numeric(pooled$qbar),
    within_variance = as.numeric(pooled$ubar),
    between_variance = as.numeric(pooled$b),
    total_variance = as.numeric(pooled$t),
    se = sqrt(as.numeric(pooled$t)),
    relative_increase_variance = as.numeric(pooled$r),
    df = as.numeric(pooled$df)
  )
}

power_reference <- function(spec) {
  f2 <- as.numeric(spec$f2); u <- as.integer(spec$u); v <- as.integer(spec$v); alpha <- as.numeric(spec$alpha)
  if (!is.finite(f2) || f2 < 0 || is.na(u) || u < 1L || is.na(v) || v < 1L) {
    return(failure("POWER_INVALID_DEGREES_OF_FREEDOM", "f2 must be non-negative and u/v must both be positive"))
  }
  if (!is.finite(alpha) || alpha <= 0 || alpha >= 1) return(failure("POWER_INVALID_ALPHA", "alpha must be strictly between zero and one"))
  if (!requireNamespace("pwr", quietly = TRUE)) stop("pwr is required for the primary f2 reference")
  calculated <- pwr::pwr.f2.test(u = u, v = v, f2 = f2, sig.level = alpha)
  ncp <- f2 * (u + v + 1)
  list(f2 = f2, u = u, v = v, n = as.integer(u + v + 1L), alpha = alpha,
    ncp = ncp, f_crit = stats::qf(1 - alpha, u, v), power = as.numeric(calculated$power))
}

tost_reference <- function(spec, data) {
  parameters <- spec$parameters; fields <- spec$data
  low <- as.numeric(parameters$lowBound); high <- as.numeric(parameters$highBound); alpha <- as.numeric(parameters$alpha)
  method <- if (is.null(parameters$varianceMethod)) "student" else as.character(parameters$varianceMethod)
  if (!is.finite(low) || !is.finite(high) || low >= high) return(failure("TOST_INVALID_BOUNDS", "The lower equivalence bound must be strictly less than the upper bound"))
  if (!all(c(fields$groupVar, fields$outcomeVar) %in% names(data))) return(failure("TOST_INVALID_GROUP_LAYOUT", "TOST requires exactly two observed groups"))
  frame <- data[stats::complete.cases(data[, c(fields$groupVar, fields$outcomeVar)]), , drop = FALSE]
  groups <- factor(frame[[fields$groupVar]])
  levels <- levels(groups)
  if (length(levels) != 2L) return(failure("TOST_INVALID_GROUP_LAYOUT", "TOST requires exactly two observed groups"))
  first <- as.numeric(frame[[fields$outcomeVar]][groups == levels[[1]]]); second <- as.numeric(frame[[fields$outcomeVar]][groups == levels[[2]]])
  if (length(first) < 2L || length(second) < 2L) return(failure("TOST_INSUFFICIENT_SAMPLE", "Each TOST group requires at least two observations"))
  # The primary reference deliberately uses the documented raw-scale
  # Student/Welch equations in base R.  This avoids binding the Golden contract
  # to a changing TOSTER API while remaining independent from the R production
  # adapter and the SciPy secondary reference.
  difference <- mean(first) - mean(second); var_first <- stats::var(first); var_second <- stats::var(second)
  if (identical(method, "welch")) {
    component_first <- var_first / length(first); component_second <- var_second / length(second)
    standard_error <- sqrt(component_first + component_second)
    degrees <- (component_first + component_second)^2 / (component_first^2 / (length(first) - 1) + component_second^2 / (length(second) - 1))
  } else if (identical(method, "student")) {
    degrees <- length(first) + length(second) - 2L
    pooled_sd <- sqrt(((length(first) - 1) * var_first + (length(second) - 1) * var_second) / degrees)
    standard_error <- pooled_sd * sqrt(1 / length(first) + 1 / length(second))
  } else return(failure("TOST_VARIANCE_METHOD_NOT_SUPPORTED", "Only student and welch variance methods are supported"))
  if (!is.finite(standard_error) || standard_error <= 0) return(failure("TOST_STANDARD_ERROR_UNAVAILABLE", "TOST standard error is unavailable"))
  lower_t <- (difference - low) / standard_error; upper_t <- (difference - high) / standard_error
  lower_p <- stats::pt(lower_t, df = degrees, lower.tail = FALSE); upper_p <- stats::pt(upper_t, df = degrees)
  tost_p <- max(lower_p, upper_p); equivalent <- tost_p < alpha
  list(tost_results = list(mean_diff = difference, se = standard_error, df = degrees, variance_method = method,
    t_lower = lower_t, p_lower = lower_p, t_upper = upper_t, p_upper = upper_p, tost_p = tost_p,
    equivalent = equivalent, decision = if (equivalent) "equivalent" else "not_equivalent"), diagnostics = list(converged = TRUE))
}

games_howell_reference <- function(spec, data) {
  fields <- spec$data; outcome <- fields$outcomeVar; group <- fields$groupVar
  if (!all(c(outcome, group) %in% names(data))) return(failure("GAMES_HOWELL_REQUIRES_TWO_GROUPS", "Games-Howell requires at least two observed groups"))
  frame <- data[stats::complete.cases(data[, c(outcome, group)]), , drop = FALSE]; frame[[group]] <- factor(frame[[group]])
  if (nlevels(frame[[group]]) < 2L) return(failure("GAMES_HOWELL_REQUIRES_TWO_GROUPS", "Games-Howell requires at least two observed groups"))
  if (any(table(frame[[group]]) < 2L)) return(failure("GAMES_HOWELL_GROUP_REQUIRES_TWO_OBSERVATIONS", "Each Games-Howell group requires at least two observations"))
  # Base R's studentized-range distribution gives a stable, independent
  # implementation of the documented Games--Howell statistic and interval.
  levels <- levels(frame[[group]])
  summaries <- lapply(levels, function(level) { values <- frame[[outcome]][frame[[group]] == level]; list(level = level, n = length(values), mean = mean(values), variance = stats::var(values)) })
  pair_index <- utils::combn(seq_along(summaries), 2L)
  alpha <- as.numeric(spec$parameters$alpha)
  contrasts <- lapply(seq_len(ncol(pair_index)), function(index) {
    left <- summaries[[pair_index[1, index]]]; right <- summaries[[pair_index[2, index]]]
    left_component <- left$variance / left$n; right_component <- right$variance / right$n
    standard_error <- sqrt(left_component + right_component)
    degrees <- (left_component + right_component)^2 / (left_component^2 / (left$n - 1L) + right_component^2 / (right$n - 1L))
    difference <- right$mean - left$mean; q_statistic <- sqrt(2) * abs(difference) / standard_error
    critical <- stats::qtukey(1 - alpha, nmeans = length(levels), df = degrees) / sqrt(2)
    list(comparison = paste0(right$level, " - ", left$level), estimate = difference, se = standard_error, df = degrees,
      q_statistic = q_statistic, p_adjusted = stats::ptukey(q_statistic, nmeans = length(levels), df = degrees, lower.tail = FALSE),
      ci_lower = difference - critical * standard_error, ci_upper = difference + critical * standard_error)
  })
  list(contrasts = contrasts, diagnostics = list(converged = TRUE))
}

randomization_reference <- function(spec, data) {
  fields <- spec$data; treatment_name <- fields$treatmentVar; outcome_name <- fields$outcomeVar; block_name <- fields$blockVar
  if (!all(c(treatment_name, outcome_name) %in% names(data))) return(failure("RANDOMIZATION_COLUMNS_MISSING", "Treatment and outcome columns are required"))
  if (!is.null(spec$parameters$assignmentLength) && as.integer(spec$parameters$assignmentLength) != nrow(data)) return(failure("RANDOMIZATION_ASSIGNMENT_LENGTH_MISMATCH", "Assignment length does not match the outcome vector"))
  treatment <- as.numeric(data[[treatment_name]]); outcome <- as.numeric(data[[outcome_name]])
  if (any(!is.finite(treatment)) || any(!is.finite(outcome)) || !all(treatment %in% c(0, 1)) || !any(treatment == 1) || !any(treatment == 0)) return(failure("RANDOMIZATION_INVALID_ASSIGNMENT", "Treatment must contain both binary assignment values"))
  if (!is.null(block_name) && !block_name %in% names(data)) return(failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Declared block variable is missing"))
  blocks <- if (is.null(block_name)) list(all = seq_along(outcome)) else split(seq_along(outcome), data[[block_name]])
  options <- lapply(blocks, function(indices) { treated <- sum(treatment[indices] == 1); if (treated < 1L || treated >= length(indices)) return(NULL); utils::combn(indices, treated, simplify = FALSE) })
  if (any(vapply(options, is.null, logical(1)))) return(failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Every block requires treated and control observations"))
  assignments <- list(integer(0)); for (block_options in options) assignments <- unlist(lapply(assignments, function(prefix) lapply(block_options, function(indices) c(prefix, indices))), recursive = FALSE)
  observed <- mean(outcome[treatment == 1]) - mean(outcome[treatment == 0])
  statistics <- vapply(assignments, function(indices) mean(outcome[indices]) - mean(outcome[-indices]), numeric(1))
  list(ate = observed, permutation_count = length(assignments), p_value_two_sided = mean(abs(statistics) >= abs(observed) - 1e-12),
    p_value_one_sided = mean(statistics >= observed - 1e-12), diagnostics = list(converged = TRUE))
}

result <- switch(capability,
  "imputation.pooling.linear.rubin.v1" = rubin_reference(as.numeric(data$q), as.numeric(data$u), spec$completeDataDf),
  "power.regression.f2.analytic.v1" = power_reference(spec),
  "equivalence.tost.two_sample.v1" = tost_reference(spec, data),
  "experiment.posthoc.games_howell.v1" = games_howell_reference(spec, data),
  "experiment.randomization.inference.v1" = randomization_reference(spec, data),
  stop(paste0("REFERENCE_CAPABILITY_NOT_IMPLEMENTED: ", capability), call. = FALSE)
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE, null = "null", na = "null", digits = NA)
