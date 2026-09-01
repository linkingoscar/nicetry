construct_validity <- build_construct_validity(metadata$constructs, item_complete, cfa)
construct_score_ids <- vapply(construct_validity, function(row) row$scoreId, character(1))
construct_correlation_source <- "observed construct-score correlations"
construct_correlation <- if (
  isTRUE(cfa$available) &&
  length(cfa$constructIds) == length(metadata$constructs) &&
  identical(unlist(cfa$constructIds), construct_ids)
) {
  construct_correlation_source <- "CFA latent-factor correlations"
  do.call(rbind, lapply(cfa$factorCorrelations, unlist))
} else if (length(construct_score_ids) >= 2) {
  cor(data[, construct_score_ids, drop = FALSE], use = "pairwise.complete.obs")
} else {
  matrix(1, 1, 1)
}
fornell <- lapply(seq_along(construct_validity), function(i) {
  row <- as.list(as.numeric(construct_correlation[i, ]))
  row[[i]] <- construct_validity[[i]]$sqrtAve
  row
})
for (i in seq_along(construct_validity)) {
  other <- abs(construct_correlation[i, -i, drop = TRUE])
  complete_evidence <- isTRUE(cfa$available) && is.finite(construct_validity[[i]]$sqrtAve) && isTRUE(all(is.finite(other)))
  status <- if (!complete_evidence) {
    "not_evaluable"
  } else if (length(other) == 0 || isTRUE(all(construct_validity[[i]]$sqrtAve > other))) {
    "pass"
  } else {
    "fail"
  }
  construct_validity[[i]]$discriminantValidityStatus <- status
  construct_validity[[i]]$discriminantValidityPass <- if (status == "not_evaluable") NA else identical(status, "pass")
}

htmt_correlation_type <- if (identical(measurement_item_scale, "ordinal")) {
  "polychoric"
} else if (identical(measurement_item_scale, "continuous")) {
  "pearson"
} else {
  NULL
}
htmt_reason <- if (is.null(htmt_correlation_type)) {
  "MIXED_SCALE_HTMT_REQUIRES_EXPLICIT_HETEROGENEOUS_CORRELATION_MATRIX"
} else {
  NULL
}
htmt_result <- if (
  !is.null(htmt_correlation_type) && length(metadata$constructs) >= 2 &&
  ncol(item_complete) >= 2
) {
  tryCatch(
    list(
      available = TRUE,
      matrix = calc_htmt_matrix(
        item_complete, metadata$constructs, correlation_type = htmt_correlation_type
      )
    ),
    error = function(error) list(available = FALSE, reason = conditionMessage(error))
  )
} else {
  list(available = FALSE, reason = htmt_reason)
}
htmt_available <- isTRUE(htmt_result$available)
if (!htmt_available && !is.null(htmt_result$reason)) htmt_reason <- htmt_result$reason
if (htmt_available) {
  htmt_flag <- flag_undefined_htmt(htmt_result$matrix, metadata$constructs)
  htmt_mat <- htmt_flag$mat
  htmt_undefined_pairs <- htmt_flag$undefinedPairs
} else {
  construct_count <- length(metadata$constructs)
  htmt_mat <- matrix(NA_real_, construct_count, construct_count)
  diag(htmt_mat) <- 1
  htmt_undefined_pairs <- list()
}
htmt <- lapply(seq_len(nrow(htmt_mat)), function(index) as.list(as.numeric(htmt_mat[index, ])))

write_progress("validity_bootstrap", 0.72)
check_cancel()
htmt_ci <- if (htmt_available && !non_iid_context && nrow(item_complete) >= 10 && ncol(item_complete) >= 2) {
  htmt_bootstrap(
    item_complete, metadata$constructs, reps = 500, seed = as.integer(options$randomSeed),
    correlation_type = htmt_correlation_type,
    confidence_level = confidence_level
  )
} else {
  construct_count <- length(metadata$constructs)
  list(
    lower = matrix(NA_real_, construct_count, construct_count),
    upper = matrix(NA_real_, construct_count, construct_count),
    replicates = 0L, seed = as.integer(options$randomSeed),
    confidenceLevel = confidence_level, confidenceIntervalMethod = "bootstrap_percentile",
    parallelBackend = "sequential", parallelWorkers = 1L,
    rngStrategy = "deterministic per-replicate seeds"
  )
}

validity <- list(
  constructs = construct_validity,
  constructLabels = lapply(metadata$constructs, function(construct) construct$label),
  fornellCorrelationSource = construct_correlation_source,
  htmtAvailable = htmt_available,
  htmtReason = htmt_reason,
  htmtCorrelationSource = if (is.null(htmt_correlation_type)) "unavailable_mixed_item_scales" else htmt_correlation_type,
  htmtMethodExecution = list(
    requestedMethod = if (identical(measurement_item_scale, "ordinal")) {
      "polychoric_HTMT"
    } else if (identical(measurement_item_scale, "continuous")) {
      "pearson_HTMT"
    } else {
      "heterogeneous_correlation_HTMT_for_mixed_item_scales"
    },
    executedMethod = if (htmt_available) {
      paste0(htmt_correlation_type, if (non_iid_context) "_descriptive_HTMT" else "_HTMT")
    } else {
      "not_run"
    },
    fallbackApplied = FALSE, fallbackReason = htmt_reason,
    affectedOutputs = if (htmt_available) list() else as.list(c("htmt", "htmtCiLower", "htmtCiUpper")),
    interpretationBoundary = if (non_iid_context && htmt_available) {
      "HTMT 系数仅作描述；普通逐行 bootstrap 未运行，正式推断需要按聚类/重复测量重抽样或相应测量模型。"
    } else if (identical(htmt_correlation_type, "polychoric")) {
      "HTMT 与有序 CFA 使用 polychoric 相关；结果仍是区分效度诊断，不是自动通过/失败裁决。"
    } else if (identical(htmt_correlation_type, "pearson")) {
      "HTMT 使用连续题项 Pearson 相关；结果是区分效度诊断，不是自动通过/失败裁决。"
    } else {
      "混合尺度 HTMT 在没有显式异质相关矩阵和估计规格时不运行，禁止静默退回 Pearson。"
    }
  ),
  htmtInferenceAvailable = htmt_available && !non_iid_context,
  htmtInferenceReason = if (non_iid_context && htmt_available) {
    paste0(non_iid_reason_prefix, "_REQUIRE_DEPENDENCE_AWARE_BOOTSTRAP_OR_MEASUREMENT_MODEL")
  } else {
    htmt_reason
  },
  htmtConfidenceLevel = htmt_ci$confidenceLevel,
  htmtConfidenceIntervalMethod = htmt_ci$confidenceIntervalMethod,
  fornellLarcker = fornell, htmt = htmt,
  htmtCiLower = mat_to_list(htmt_ci$lower), htmtCiUpper = mat_to_list(htmt_ci$upper),
  methodExecution = build_validity_method_execution(construct_validity, cfa)
)
