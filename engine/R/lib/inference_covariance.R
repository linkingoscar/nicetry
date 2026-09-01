# Shared covariance estimators for inference paths.
#
# HC3 is deliberately implemented here as the single source of truth.  Callers
# may keep a separately declared classical estimator, but this helper never
# substitutes it for a requested HC3 covariance.

researchpath_scalar_or_na <- function(value) {
  if (length(value) != 1L || !is.numeric(value) || !is.finite(value)) {
    return(NA_real_)
  }
  as.numeric(value)
}

researchpath_integer_or_na <- function(value) {
  if (length(value) != 1L || !is.numeric(value) || !is.finite(value)) {
    return(NA_integer_)
  }
  as.integer(value)
}

researchpath_hc3_failure <- function(
  reason,
  maximum_leverage = NA_real_,
  rank = NA_integer_,
  parameter_count = NA_integer_
) {
  result <- list(
    covariance = NULL,
    available = FALSE,
    requestedMethod = "HC3",
    executedMethod = "not_run",
    fallbackApplied = FALSE,
    fallbackReason = as.character(reason),
    maximumLeverage = researchpath_scalar_or_na(maximum_leverage),
    rank = researchpath_integer_or_na(rank),
    parameterCount = researchpath_integer_or_na(parameter_count)
  )
  # Compatibility metadata for older internal consumers.  The canonical
  # fields above are requestedMethod/executedMethod.
  result$executedStandardErrorMethod <- result$executedMethod
  result
}

researchpath_hc3_execution_metadata <- function(result) {
  result[c(
    "available", "requestedMethod", "executedMethod", "fallbackApplied",
    "fallbackReason", "maximumLeverage", "rank", "parameterCount"
  )]
}

researchpath_hc3_covariance <- function(
  fit,
  leverage_tolerance = 1e-12,
  condition_number_limit = 1e12
) {
  design <- tryCatch(
    stats::model.matrix(fit),
    error = function(error) {
      error
    }
  )
  if (inherits(design, "error")) {
    return(researchpath_hc3_failure(
      paste0("HC3_UNDEFINED_MODEL_MATRIX: ", conditionMessage(design))
    ))
  }

  parameter_count <- ncol(design)
  rank <- tryCatch(
    qr(design, tol = 1e-10)$rank,
    error = function(error) NA_integer_
  )
  if (!is.finite(rank) || rank < parameter_count) {
    return(researchpath_hc3_failure(
      "HC3_UNDEFINED_RANK_DEFICIENT",
      rank = rank,
      parameter_count = parameter_count
    ))
  }

  leverage <- tryCatch(
    as.numeric(stats::hatvalues(fit)),
    error = function(error) NULL
  )
  if (is.null(leverage) || length(leverage) != nrow(design) || any(!is.finite(leverage))) {
    return(researchpath_hc3_failure(
      "HC3_UNDEFINED_LEVERAGE_UNAVAILABLE",
      rank = rank,
      parameter_count = parameter_count
    ))
  }
  maximum_leverage <- max(leverage)
  if (any(leverage >= 1 - leverage_tolerance)) {
    return(researchpath_hc3_failure(
      "HC3_UNDEFINED_LEVERAGE_ONE",
      maximum_leverage = maximum_leverage,
      rank = rank,
      parameter_count = parameter_count
    ))
  }

  condition_number <- tryCatch(kappa(design, exact = TRUE), error = function(error) Inf)
  if (!is.finite(condition_number) || condition_number > condition_number_limit) {
    return(researchpath_hc3_failure(
      "HC3_UNDEFINED_NEAR_SINGULAR",
      maximum_leverage = maximum_leverage,
      rank = rank,
      parameter_count = parameter_count
    ))
  }

  failure <- NULL
  covariance <- tryCatch({
    if (inherits(fit, "glm")) {
      working_weights <- as.numeric(fit$weights)
      working_residuals <- as.numeric(stats::residuals(fit, type = "working"))
      if (length(working_weights) != nrow(design) || any(!is.finite(working_weights))) {
        stop("HC3_UNDEFINED_MODEL_WEIGHTS")
      }
      if (length(working_residuals) != nrow(design) || any(!is.finite(working_residuals))) {
        stop("HC3_UNDEFINED_WORKING_RESIDUALS")
      }
      bread <- solve(crossprod(design, design * working_weights))
      adjusted_score <- working_weights * working_residuals / (1 - leverage)
    } else {
      residuals <- as.numeric(stats::residuals(fit))
      if (length(residuals) != nrow(design) || any(!is.finite(residuals))) {
        stop("HC3_UNDEFINED_RESIDUALS")
      }
      bread <- solve(crossprod(design))
      adjusted_score <- residuals / (1 - leverage)
    }
    meat <- crossprod(design * adjusted_score)
    estimate_covariance <- bread %*% meat %*% bread
    if (any(!is.finite(estimate_covariance)) || any(diag(estimate_covariance) < 0)) {
      stop("HC3_UNDEFINED_COVARIANCE")
    }
    estimate_covariance
  }, error = function(error) {
    failure <<- researchpath_hc3_failure(
      paste0("HC3_UNDEFINED_COVARIANCE: ", conditionMessage(error)),
      maximum_leverage = maximum_leverage,
      rank = rank,
      parameter_count = parameter_count
    )
    NULL
  })
  if (is.null(covariance)) return(failure)

  result <- list(
    covariance = covariance,
    available = TRUE,
    requestedMethod = "HC3",
    executedMethod = "HC3",
    fallbackApplied = FALSE,
    fallbackReason = NULL,
    maximumLeverage = researchpath_scalar_or_na(maximum_leverage),
    rank = researchpath_integer_or_na(rank),
    parameterCount = researchpath_integer_or_na(parameter_count)
  )
  result$executedStandardErrorMethod <- result$executedMethod
  result
}

researchpath_covariance_available <- function(covariance) {
  if (is.null(covariance)) return(FALSE)
  declared <- attr(covariance, "researchpath_covariance_available", exact = TRUE)
  if (!is.null(declared)) return(isTRUE(declared))
  all(is.finite(covariance))
}

researchpath_unavailable_covariance <- function(fit, execution) {
  coefficient_names <- names(stats::coef(fit))
  covariance <- matrix(
    NA_real_,
    nrow = length(coefficient_names),
    ncol = length(coefficient_names),
    dimnames = list(coefficient_names, coefficient_names)
  )
  attr(covariance, "researchpath_standard_error_method") <- execution$executedMethod
  attr(covariance, "researchpath_covariance_available") <- FALSE
  attr(covariance, "researchpath_covariance_reason") <- execution$fallbackReason
  covariance
}

researchpath_confidence_interval_method <- function(
  covariance,
  is_glm,
  requested_standard_errors
) {
  if (!researchpath_covariance_available(covariance)) return("inference_unavailable")
  if (isTRUE(is_glm)) {
    if (identical(requested_standard_errors, "hc3")) "hc3_z" else "wald_z"
  } else if (identical(requested_standard_errors, "hc3")) {
    "hc3_t"
  } else {
    "classical_t"
  }
}
