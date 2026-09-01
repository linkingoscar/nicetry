fit_relative_importance <- function(data, outcome_id, predictor_ids, control_ids, label_lookup) {
  predictor_ids <- unique(predictor_ids)
  control_ids <- unique(control_ids)
  predictor_count <- length(predictor_ids)
  if (predictor_count < 2L) {
    return(list(available = FALSE, reason = "相对重要性至少需要两个焦点预测变量"))
  }
  if (predictor_count > 10L) {
    return(list(
      available = FALSE,
      reason = "精确 Shapley/LMG 分解最多支持 10 个焦点预测变量"
    ))
  }
  required <- unique(c(outcome_id, control_ids, predictor_ids))
  frame <- data[, required, drop = FALSE]
  frame <- frame[complete.cases(frame), , drop = FALSE]
  if (nrow(frame) <= length(required) + 2L) {
    return(list(available = FALSE, reason = "完整案例不足以分解相对重要性"))
  }

  subset_count <- bitwShiftL(1L, predictor_count)
  r_squared <- rep(NA_real_, subset_count)
  predictor_bits <- bitwShiftL(1L, seq_len(predictor_count) - 1L)
  for (mask in 0:(subset_count - 1L)) {
    included <- predictor_ids[bitwAnd(mask, predictor_bits) != 0L]
    terms <- c(control_ids, included)
    model_formula <- if (length(terms) > 0L) {
      reformulate(terms, response = outcome_id)
    } else {
      reformulate("1", response = outcome_id)
    }
    fit <- tryCatch(lm(model_formula, data = frame), error = function(error) NULL)
    if (is.null(fit)) {
      return(list(available = FALSE, reason = "相对重要性子集模型不可估计"))
    }
    r_squared[[mask + 1L]] <- summary(fit)$r.squared
  }
  if (any(!is.finite(r_squared))) {
    return(list(available = FALSE, reason = "相对重要性子集模型出现非有限 R²"))
  }

  contributions <- numeric(predictor_count)
  for (predictor_index in seq_len(predictor_count)) {
    bit <- predictor_bits[[predictor_index]]
    masks <- 0:(subset_count - 1L)
    masks <- masks[bitwAnd(masks, bit) == 0L]
    for (mask in masks) {
      subset_size <- sum(bitwAnd(mask, predictor_bits) != 0L)
      weight <- factorial(subset_size) * factorial(
        predictor_count - subset_size - 1L
      ) / factorial(predictor_count)
      contributions[[predictor_index]] <- contributions[[predictor_index]] +
        weight * (r_squared[[bitwOr(mask, bit) + 1L]] - r_squared[[mask + 1L]])
    }
  }

  base_r_squared <- r_squared[[1L]]
  full_r_squared <- r_squared[[subset_count]]
  incremental_r_squared <- full_r_squared - base_r_squared
  rows <- lapply(seq_along(predictor_ids), function(index) {
    contribution <- contributions[[index]]
    list(
      id = predictor_ids[[index]],
      label = label_lookup(predictor_ids[[index]]),
      contribution = finite_number(contribution),
      percentIncrementalRSquared = if (incremental_r_squared > 0) {
        finite_number(100 * contribution / incremental_r_squared)
      } else {
        NULL
      },
      rank = as.integer(rank(-contributions, ties.method = "min")[[index]])
    )
  })
  rows <- rows[order(vapply(rows, function(row) row$rank, integer(1)))]

  list(
    available = TRUE,
    n = nrow(frame),
    outcomeId = outcome_id,
    outcomeLabel = label_lookup(outcome_id),
    predictorCount = predictor_count,
    controlIds = as.list(control_ids),
    baseRSquared = finite_number(base_r_squared),
    fullRSquared = finite_number(full_r_squared),
    incrementalRSquared = finite_number(incremental_r_squared),
    contributionSum = finite_number(sum(contributions)),
    rows = rows,
    method = "exact Shapley/LMG decomposition of incremental R-squared conditional on controls",
    subsetModelCount = subset_count
  )
}
