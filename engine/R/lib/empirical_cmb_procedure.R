marker_res <- if (!is.null(options$markerVariableId)) calc_marker_variable_cmb(data, options$markerVariableId, metadata$constructs) else list(available = FALSE)
ulmc_res <- tryCatch(fit_ulmc_cmb_model(item_complete, metadata$constructs), error = function(e) list(available = FALSE, reason = as.character(e)))

common_method <- list(
  available = length(eigenvalues) > 0,
  completeCases = nrow(item_complete), itemCount = ncol(item_complete),
  firstFactorVariancePercent = if (length(eigenvalues) > 0) finite_number(100 * eigenvalues[1] / sum(eigenvalues)) else NA_real_,
  eigenvaluesAboveOne = sum(eigenvalues > 1),
  method = if (identical(item_correlation_type, "polychoric")) {
    "Harman single-factor diagnostic on the polychoric item correlation matrix with Marker Variable & ULMC support"
  } else {
    "Harman single-factor diagnostic with Marker Variable & ULMC support"
  },
  correlationType = item_correlation_type,
  correlationReason = item_correlation_reason,
  markerVariable = marker_res,
  ulmc = ulmc_res
)
