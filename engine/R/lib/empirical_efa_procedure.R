write_progress("factor_analysis", 0.38)
check_cancel()
parallel_res <- NULL
parallel_fallback_reason <- NULL
if (
  identical(options$factorCountMethod, "parallel_analysis") &&
  !is.null(item_correlation) &&
  ncol(item_complete) >= 3 &&
  nrow(item_complete) >= 10
) {
  parallel_res <- tryCatch(
    run_parallel_analysis(
      item_complete,
      as.integer(options$parallelIterations),
      as.integer(options$randomSeed),
      correlation_type = item_correlation_type
    ),
    error = function(e) {
      parallel_fallback_reason <<- paste0(
        "平行分析未能在当前数据上完成（", conditionMessage(e),
        "），已回退到界面声明的固定因子数；请核对并行迭代数与数据规模。"
      )
      NULL
    }
  )
}

factor_method <- options$factorCountMethod
if (
  identical(factor_method, "parallel_analysis") &&
  isTRUE(parallel_res$available) &&
  !is.null(parallel_res$recommendedFactorCount)
) {
  requested_factors <- parallel_res$recommendedFactorCount
} else if (identical(factor_method, "parallel_analysis")) {
  requested_factors <- max(1L, as.integer(options$factorCount))
  if (is.null(parallel_fallback_reason)) {
    parallel_fallback_reason <- paste0(
      "平行分析未返回可用因子数建议（",
      if (is.null(parallel_res$reason)) "unknown_reason" else parallel_res$reason,
      "），已回退到界面声明的固定因子数。"
    )
  }
} else if (identical(factor_method, "kaiser") && !is.null(eigenvalues)) {
  requested_factors <- sum(eigenvalues > 1.0)
  if (requested_factors < 1) requested_factors <- 1
} else {
  requested_factors <- max(1L, as.integer(options$factorCount))
}

maximum_factors <- max(1L, min(ncol(item_complete) - 1L, floor((nrow(item_complete) - 1L) / 2L)))
factor_count <- if (requested_factors < 1L) 0L else min(requested_factors, maximum_factors)
efa_method <- "unavailable"
efa_loadings <- list()
factor_labels <- paste0("F", seq_len(factor_count))
factor_correlations <- NULL
structure_loadings <- NULL
efa_rotation <- if (identical(options$rotation, "promax")) "promax" else "varimax"
efa_execution <- unavailable_empirical_efa_execution(efa_rotation)
efa_reason <- NULL

efa_block <- empirical_fit_efa_block(
  item_complete, factor_count, efa_rotation, item_correlation,
  item_correlation_type, label_for, finite_number
)
efa_method <- efa_block$method
efa_execution <- efa_block$execution
efa_loadings <- efa_block$loadings
factor_correlations <- efa_block$factorCorrelations
structure_loadings <- efa_block$structureLoadings
if (!is.null(efa_block$reason)) efa_reason <- efa_block$reason
if (!is.null(item_correlation_reason) && identical(item_correlation_type, "polychoric")) {
  efa_reason <- item_correlation_reason
}

efa <- list(
  available = length(efa_loadings) > 0, requestedFactorCount = requested_factors,
  reason = if (!is.null(efa_reason)) {
    efa_reason
  } else if (factor_count == 0L) {
    "factor_retention_diagnostic_recommended_zero_factors"
  } else {
    NULL
  },
  factorCount = factor_count, factorLabels = as.list(factor_labels), method = efa_method,
  methodExecution = efa_execution,
  rotation = efa_rotation,
  itemScale = if (identical(item_correlation_type, "polychoric")) "ordinal" else "continuous",
  correlationType = item_correlation_type,
  requestedCorrelationType = item_correlation_type,
  eigenvalues = as.list(as.numeric(eigenvalues)), loadings = efa_loadings,
  factorCorrelations = if (is.null(factor_correlations)) NULL else lapply(seq_len(factor_count), function(index) as.list(as.numeric(factor_correlations[index, ]))),
  structureMatrix = structure_loadings,
  parallelAnalysis = parallel_res
)
if (non_iid_context) {
  efa$clusterAdjustment <- "none_descriptive_measurement_preparation_only"
  efa$methodExecution$interpretationBoundary <- paste0(
    efa$methodExecution$interpretationBoundary,
    " 当前数据行非独立；载荷只作测量准备，未使用多层/纵向因子模型或依赖结构稳健推断。"
  )
}
