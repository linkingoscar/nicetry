flag_undefined_htmt <- function(htmt_mat, constructs) {
  undefined_pairs <- list()
  if (length(constructs) >= 2L) {
    for (row in seq_len(nrow(htmt_mat))) {
      for (col in seq_len(ncol(htmt_mat))) {
        if (row >= col) next
        value <- htmt_mat[row, col]
        if (is.infinite(value) || is.nan(value)) {
          undefined_pairs[[length(undefined_pairs) + 1L]] <- paste0(
            constructs[[row]]$label, " × ", constructs[[col]]$label
          )
          htmt_mat[row, col] <- htmt_mat[col, row] <- NA_real_
        }
      }
    }
  }
  list(mat = htmt_mat, undefinedPairs = undefined_pairs)
}

htmt_undefined_warning <- function(pairs) {
  list(
    code = "HTMT_UNDEFINED",
    severity = "warning",
    message = sprintf(
      "以下构念对的 HTMT 因题项相关矩阵退化（零变异或完全相关）无法定义（已置为空）：%s。",
      paste(pairs, collapse = "、")
    )
  )
}

partial_correlation_undefined_warning <- function(pairs) {
  list(
    code = "PARTIAL_CORRELATION_UNDEFINED",
    severity = "warning",
    message = sprintf(
      "以下变量对的偏相关因完全共线或零残差变异无法定义（已置为空）：%s。",
      paste(pairs, collapse = "、")
    )
  )
}

underdetermined_regression_warning <- function(n) {
  list(
    code = "REGRESSION_UNDERDETERMINED",
    severity = "warning",
    message = sprintf(
      "分层回归完整案例 N=%d 少于或等于待估参数，R²/ΔR² 等统计量无解释价值，该区块已标记为不可解释。",
      n
    )
  )
}

compute_factorability <- function(item_correlation, item_complete) {
  kmo_value <- bartlett_statistic <- bartlett_p <- NA_real_
  bartlett_df <- 0L
  kmo_skipped_reason <- NULL
  if (!is.null(item_correlation)) {
    inverse <- NULL
    if (ncol(item_correlation) <= 800L) {
      inverse <- tryCatch(solve(item_correlation), error = function(error) NULL)
    } else {
      kmo_skipped_reason <- sprintf("题项数 %d 超出 KMO 资源预算（800），相关矩阵求逆已跳过。", ncol(item_correlation))
    }
    if (!is.null(inverse)) {
      partial <- -cov2cor(inverse)
      diag(partial) <- 0
      correlations_squared <- item_correlation^2
      diag(correlations_squared) <- 0
      partial_squared <- partial^2
      kmo_value <- sum(correlations_squared) / (sum(correlations_squared) + sum(partial_squared))
    }
    determinant <- determinant(item_correlation, logarithm = TRUE)
    if (determinant$sign > 0) {
      p <- ncol(item_complete)
      n <- nrow(item_complete)
      bartlett_statistic <- -(n - 1 - (2 * p + 5) / 6) * as.numeric(determinant$modulus)
      bartlett_df <- as.integer(p * (p - 1) / 2)
      bartlett_p <- pchisq(bartlett_statistic, bartlett_df, lower.tail = FALSE)
    }
  }
  list(
    kmo = finite_number(kmo_value),
    kmoSkippedReason = kmo_skipped_reason,
    bartlett = list(statistic = finite_number(bartlett_statistic), degreesOfFreedom = bartlett_df, pValue = finite_number(bartlett_p)),
    completeCases = nrow(item_complete)
  )
}
