# Cluster aggregation diagnostics for OB/CB questionnaire research.
#
# ICC(1) and ICC(2) use a one-way random-effects ANOVA with the effective
# cluster size for unbalanced groups. rwg(j) uses a rectangular null
# distribution and scales its expected variance to the construct score's
# item count and mean/sum aggregation rule.

aggregation_unavailable <- function(
  outcome_id,
  outcome_label,
  code,
  message
) {
  list(
    id = outcome_id,
    label = outcome_label,
    available = FALSE,
    reasonCode = code,
    reason = message
  )
}

calc_aggregation_diagnostics <- function(
  data,
  outcome_id,
  outcome_label,
  cluster_id,
  scale_min,
  scale_max,
  item_count,
  aggregation_method = "mean"
) {
  if (!outcome_id %in% names(data) || !cluster_id %in% names(data)) {
    return(aggregation_unavailable(
      outcome_id,
      outcome_label,
      "AGGREGATION_COLUMN_NOT_FOUND",
      "量表得分或 cluster 变量不存在。"
    ))
  }
  if (
    !is.finite(scale_min) ||
    !is.finite(scale_max) ||
    scale_max <= scale_min ||
    !is.finite(item_count) ||
    item_count < 1
  ) {
    return(aggregation_unavailable(
      outcome_id,
      outcome_label,
      "AGGREGATION_SCALE_INVALID",
      "量表范围或题项数无效，无法计算 rwg(j)。"
    ))
  }

  frame <- data.frame(
    outcome = suppressWarnings(as.numeric(data[[outcome_id]])),
    cluster = data[[cluster_id]]
  )
  frame <- frame[is.finite(frame$outcome) & !is.na(frame$cluster), , drop = FALSE]
  if (nrow(frame) < 4) {
    return(aggregation_unavailable(
      outcome_id,
      outcome_label,
      "AGGREGATION_INSUFFICIENT_OBSERVATIONS",
      "有效观测少于 4，无法计算聚合诊断。"
    ))
  }

  frame$cluster <- droplevels(as.factor(frame$cluster))
  cluster_sizes <- table(frame$cluster)
  cluster_count <- length(cluster_sizes)
  if (cluster_count < 2 || nrow(frame) <= cluster_count) {
    return(aggregation_unavailable(
      outcome_id,
      outcome_label,
      "AGGREGATION_INSUFFICIENT_CLUSTERS",
      "至少需要两个 cluster，且需存在 cluster 内重复观测。"
    ))
  }

  fit <- stats::aov(outcome ~ cluster, data = frame)
  fit_table <- summary(fit)[[1]]
  ms_between <- as.numeric(fit_table[1, "Mean Sq"])
  ms_within <- as.numeric(fit_table[2, "Mean Sq"])
  total_n <- sum(cluster_sizes)
  effective_cluster_size <- (
    total_n - sum(cluster_sizes^2) / total_n
  ) / (cluster_count - 1)
  if (!is.finite(effective_cluster_size) || effective_cluster_size <= 1) {
    return(aggregation_unavailable(
      outcome_id,
      outcome_label,
      "AGGREGATION_CLUSTER_SIZE_INVALID",
      "有效平均 cluster 规模不足。"
    ))
  }

  denominator <- ms_between + (effective_cluster_size - 1) * ms_within
  icc1 <- if (is.finite(denominator) && abs(denominator) > .Machine$double.eps) {
    (ms_between - ms_within) / denominator
  } else {
    NA_real_
  }
  icc2 <- if (is.finite(ms_between) && abs(ms_between) > .Machine$double.eps) {
    (ms_between - ms_within) / ms_between
  } else {
    NA_real_
  }

  category_count <- scale_max - scale_min + 1
  discrete_scale <- is.finite(category_count) &&
    category_count >= 2 &&
    abs(category_count - round(category_count)) <= 1e-8
  expected_item_variance <- if (discrete_scale) {
    (round(category_count)^2 - 1) / 12
  } else {
    NA_real_
  }
  expected_score_variance <- if (!is.finite(expected_item_variance)) {
    NA_real_
  } else if (identical(aggregation_method, "sum")) {
    item_count * expected_item_variance
  } else {
    expected_item_variance / item_count
  }

  eligible_clusters <- names(cluster_sizes[cluster_sizes >= 2])
  observed_variances <- vapply(eligible_clusters, function(cluster) {
    stats::var(frame$outcome[frame$cluster == cluster])
  }, numeric(1))
  rwg_values <- if (
    length(observed_variances) > 0 &&
    is.finite(expected_score_variance) &&
    expected_score_variance > 0
  ) {
    1 - observed_variances / expected_score_variance
  } else {
    numeric(0)
  }
  finite_rwg <- rwg_values[is.finite(rwg_values)]

  list(
    id = outcome_id,
    label = outcome_label,
    available = TRUE,
    observations = as.integer(nrow(frame)),
    clusterCount = as.integer(cluster_count),
    eligibleRwgClusterCount = as.integer(length(finite_rwg)),
    minimumClusterSize = as.integer(min(cluster_sizes)),
    maximumClusterSize = as.integer(max(cluster_sizes)),
    averageClusterSize = as.numeric(effective_cluster_size),
    icc1 = finite_number(icc1),
    icc2 = finite_number(icc2),
    designEffect = finite_number(
      1 + (effective_cluster_size - 1) * icc1
    ),
    rwg = list(
      nullDistribution = "rectangular",
      itemCount = as.integer(item_count),
      scoreAggregation = aggregation_method,
      expectedScoreVariance = finite_number(expected_score_variance),
      mean = if (length(finite_rwg) > 0) {
        finite_number(mean(finite_rwg))
      } else {
        NULL
      },
      median = if (length(finite_rwg) > 0) {
        finite_number(stats::median(finite_rwg))
      } else {
        NULL
      },
      proportionAtLeastPoint70 = if (length(finite_rwg) > 0) {
        finite_number(mean(finite_rwg >= 0.70))
      } else {
        NULL
      },
      byCluster = as.list(as.numeric(rwg_values))
    ),
    interpretation = paste(
      "ICC 与 rwg(j) 是聚合诊断，不是自动许可规则；",
      "应同时结合构念层级理论、cluster 数量和规模分布解释。"
    )
  )
}
