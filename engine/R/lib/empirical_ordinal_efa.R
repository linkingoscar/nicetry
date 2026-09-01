# Ordinal-aware helpers for the empirical base report. Kept in a focused
# module so run_empirical_analysis.R only wires the section-level boundary.

empirical_ordinal_item_ids <- function(metadata) {
  vapply(
    Filter(
      function(variable) isTRUE(variable$isItem) && variable$type %in% c("ordinal", "likert"),
      metadata$variables
    ),
    function(variable) variable$id,
    character(1)
  )
}

empirical_build_item_correlation <- function(item_complete, usable_items, ordinal_item_ids) {
  usable_ordinal_items <- intersect(ordinal_item_ids, usable_items)
  correlation_type <- if (length(usable_ordinal_items) > 0L) "polychoric" else "pearson"
  correlation <- NULL
  reason <- NULL
  if (ncol(item_complete) >= 2 && nrow(item_complete) >= 5) {
    if (identical(correlation_type, "polychoric")) {
      if (requireNamespace("lavaan", quietly = TRUE)) {
        correlation <- tryCatch(
          unclass(lavaan::lavCor(as.data.frame(item_complete), ordered = usable_ordinal_items)),
          error = function(error) {
            reason <<- paste0("ordinal_polychoric_correlation_failed: ", conditionMessage(error))
            NULL
          }
        )
      } else {
        reason <- "ordinal_polychoric_correlation_requires_lavaan"
      }
    } else {
      correlation <- cor(item_complete)
    }
  }
  list(
    correlation = correlation,
    correlationType = correlation_type,
    reason = reason
  )
}

empirical_fit_efa_block <- function(item_complete, factor_count, rotation, item_correlation,
                                    item_correlation_type, label_for, finite_number) {
  default_execution <- unavailable_empirical_efa_execution(rotation)
  if (
    factor_count < 1L || is.null(item_correlation) ||
    ncol(item_complete) < 3L || nrow(item_complete) < 10L
  ) {
    return(list(
      method = "unavailable", execution = default_execution,
      loadings = list(), factorCorrelations = NULL, structureLoadings = NULL, reason = NULL
    ))
  }
  fit <- if (identical(item_correlation_type, "polychoric")) {
    fit_empirical_efa(
      item_complete, factor_count, rotation,
      correlation_matrix = item_correlation, sample_size = nrow(item_complete),
      allow_pca_fallback = FALSE
    )
  } else {
    fit_empirical_efa(item_complete, factor_count, rotation)
  }
  if (!isTRUE(fit$available)) {
    return(list(
      method = "unavailable", execution = measurement_execution_fields(fit),
      loadings = list(), factorCorrelations = NULL, structureLoadings = NULL, reason = fit$reason
    ))
  }
  loading_matrix <- fit$loadings
  factor_correlations <- fit$factorCorrelations
  loadings <- lapply(seq_len(nrow(loading_matrix)), function(index) {
    row_name <- rownames(loading_matrix)[index]
    communality <- if (!is.null(factor_correlations)) {
      as.numeric(loading_matrix[index, , drop = FALSE] %*% factor_correlations %*%
        t(loading_matrix[index, , drop = FALSE]))
    } else {
      sum(loading_matrix[index, ]^2)
    }
    list(
      itemId = row_name, label = label_for(row_name),
      loadings = as.list(as.numeric(loading_matrix[index, ])),
      communality = finite_number(communality)
    )
  })
  structure_loadings <- NULL
  if (!is.null(factor_correlations)) {
    structure_matrix <- loading_matrix %*% factor_correlations
    structure_loadings <- lapply(seq_len(nrow(structure_matrix)), function(index) {
      as.list(as.numeric(structure_matrix[index, ]))
    })
  }
  list(
    method = fit$executedMethod, execution = measurement_execution_fields(fit),
    loadings = loadings, factorCorrelations = factor_correlations,
    structureLoadings = structure_loadings, reason = NULL
  )
}
