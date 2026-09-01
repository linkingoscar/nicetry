# Shared utility functions for time series and lagged variables

#' Create lagged variable with time gap calculation and interval tolerance filtering
create_lagged_variable <- function(data, var, id_var, lag_order, spec) {
  time <- spec$timeVariableId
  lagged_id <- paste0(var, "__lag", lag_order)
  gap_id <- paste0(time, "__gap", lag_order)
  data[[lagged_id]] <- ave(data[[var]], data[[id_var]], FUN = function(values) {
    c(rep(NA_real_, lag_order), head(values, -lag_order))
  })
  data[[gap_id]] <- ave(data[[time]], data[[id_var]], FUN = function(values) {
    values - c(rep(NA_real_, lag_order), head(values, -lag_order))
  })
  if (!is.null(spec$expectedTimeInterval)) {
    expected_gap <- spec$expectedTimeInterval * lag_order
    tolerance <- if (is.null(spec$timeIntervalTolerance)) 0 else spec$timeIntervalTolerance
    outside <- abs(data[[gap_id]] - expected_gap) > tolerance
    data[[lagged_id]][outside] <- NA_real_
  }
  list(data = data, lagged_id = lagged_id, gap_id = gap_id)
}

#' Time origin strategy
prepare_time_origin <- function(data, time_var, spec) {
  origin_strategy <- if (is.null(spec$timeOriginStrategy)) {
    "sample_mean"
  } else {
    spec$timeOriginStrategy
  }
  origin_value <- switch(
    origin_strategy,
    sample_mean = mean(data[[time_var]], na.rm = TRUE),
    first_observed = min(data[[time_var]], na.rm = TRUE),
    custom = spec$customTimeOrigin,
    stop("DIARY_TIME_ORIGIN_STRATEGY_NOT_SUPPORTED")
  )
  if (is.null(origin_value) || !is.finite(origin_value)) {
    stop("DIARY_TIME_ORIGIN_NOT_FINITE")
  }
  list(origin_strategy = origin_strategy, origin_value = origin_value)
}

#' Create polynomial time terms
prepare_time_trends <- function(data, time_var, spec) {
  origin_res <- prepare_time_origin(data, time_var, spec)
  origin_value <- origin_res$origin_value
  origin_strategy <- origin_res$origin_strategy
  
  time_centered <- paste0(time_var, "__centered")
  data[[time_centered]] <- data[[time_var]] - origin_value
  time_terms <- character(0)
  if (isTRUE(spec$includeLinearTime)) time_terms <- c(time_terms, time_centered)
  
  time_squared <- NULL
  if (isTRUE(spec$includeQuadraticTime)) {
    time_squared <- paste0(time_var, "__centered_sq")
    data[[time_squared]] <- data[[time_centered]]^2
    time_terms <- c(time_terms, time_squared)
  }
  
  time_protocol <- list(
    originStrategy = origin_strategy,
    originValue = ensure_finite(origin_value),
    centeredVariableId = time_centered,
    linearTerm = time_centered,
    quadraticTerm = time_squared,
    observedMinimum = ensure_finite(min(data[[time_var]], na.rm = TRUE)),
    observedMaximum = ensure_finite(max(data[[time_var]], na.rm = TRUE))
  )
  
  list(data = data, time_terms = time_terms, time_protocol = time_protocol)
}
