# ResearchPath R Engine - Multilevel Aggregation Evidence & ICC/rwg (WP-AGG-01)

calc_multilevel_aggregation <- function(data, outcome_var, cluster_var, scale_min = 1, scale_max = 5) {
  if (!outcome_var %in% colnames(data) || !cluster_var %in% colnames(data)) {
    stop("AGGREGATION_COLUMN_NOT_FOUND")
  }
  if (!is.finite(scale_min) || !is.finite(scale_max) || scale_max <= scale_min) {
    stop("AGGREGATION_SCALE_RANGE_INVALID")
  }

  sub_df <- data[!is.na(data[[outcome_var]]) & !is.na(data[[cluster_var]]), , drop = FALSE]
  if (nrow(sub_df) < 4) stop("AGGREGATION_INSUFFICIENT_OBSERVATIONS")
  cluster_factor <- droplevels(as.factor(sub_df[[cluster_var]]))
  n_k <- table(cluster_factor)
  if (length(n_k) < 2) stop("AGGREGATION_INSUFFICIENT_CLUSTERS")
  if (any(n_k < 2)) stop("AGGREGATION_CLUSTER_WITH_FEWER_THAN_TWO_OBSERVATIONS")

  # Always treat the declared cluster identifier as categorical. Numeric IDs
  # must not silently become a linear covariate in the ANOVA decomposition.
  fit_frame <- data.frame(
    .rp_outcome = as.numeric(sub_df[[outcome_var]]),
    .rp_cluster = cluster_factor
  )
  fit <- stats::aov(.rp_outcome ~ .rp_cluster, data = fit_frame)
  fit_s <- summary(fit)[[1]]
  ms_between <- as.numeric(fit_s["Mean Sq"][1, 1])
  ms_within <- as.numeric(fit_s["Mean Sq"][2, 1])
  n_total <- sum(n_k)
  n_bar <- (n_total - sum(n_k^2) / n_total) / (length(n_k) - 1)
  if (!is.finite(n_bar) || n_bar <= 1) stop("AGGREGATION_CLUSTER_SIZE_INVALID")

  icc1_raw <- (ms_between - ms_within) / (ms_between + (n_bar - 1) * ms_within)
  icc2_raw <- (ms_between - ms_within) / ms_between
  icc1 <- max(-1, min(1, icc1_raw))
  icc2 <- max(-1, min(1, icc2_raw))

  category_count <- floor(scale_max - scale_min) + 1
  if (category_count < 2 || abs(category_count - (scale_max - scale_min + 1)) > 1e-8) stop("AGGREGATION_DISCRETE_SCALE_REQUIRED")
  observed_values <- sub_df[[outcome_var]]
  if (any(observed_values < scale_min | observed_values > scale_max, na.rm = TRUE)) stop("AGGREGATION_SCALE_OUT_OF_RANGE")
  expected_variance <- (category_count^2 - 1) / 12
  group_vars <- tapply(observed_values, cluster_factor, stats::var)
  rwg_values <- pmax(-1, pmin(1, 1 - group_vars / expected_variance))
  mean_rwg <- mean(rwg_values, na.rm = TRUE)

  list(
    outcomeVariable = outcome_var,
    clusterVariable = cluster_var,
    scale = list(min = scale_min, max = scale_max, expectedVariance = expected_variance),
    numClusters = as.integer(length(n_k)),
    clusterSizes = as.list(as.integer(n_k)),
    averageClusterSize = as.numeric(n_bar),
    icc1 = as.numeric(icc1),
    icc1Raw = as.numeric(icc1_raw),
    icc2 = as.numeric(icc2),
    icc2Raw = as.numeric(icc2_raw),
    rwgByCluster = as.list(as.numeric(rwg_values)),
    meanRwg = as.numeric(mean_rwg),
    aggregationJustified = isTRUE(icc1 >= 0.05 && icc2 >= 0.60 && mean_rwg >= 0.70),
    diagnosticMessage = if (isTRUE(icc1 >= 0.05 && icc2 >= 0.60 && mean_rwg >= 0.70)) {
      "聚合证据达到预设 ICC(1)、ICC(2) 与 rwg 规则；仍需结合理论层级和不平衡 cluster 解释。"
    } else {
      "聚合证据未同时达到预设 ICC(1)、ICC(2) 与 rwg 规则；不应仅凭均值聚合。"
    }
  )
}
