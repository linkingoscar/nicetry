# ResearchPath R Engine - Equivalence Testing (TOST) & Multiplicity Correction (WP-EXP-05)

run_tost_equivalence <- function(data, dv, group_var, low_eqbound = -0.5, high_eqbound = 0.5,
                                 alpha = 0.05, variance_method = "student") {
  if (!dv %in% colnames(data) || !group_var %in% colnames(data)) {
    stop("指定的因变量或分组变量不存在")
  }

  sub_df <- data[!is.na(data[[dv]]) & !is.na(data[[group_var]]), ]
  group_factor <- as.factor(sub_df[[group_var]])
  levels_name <- levels(group_factor)

  if (length(levels_name) != 2) {
    stop("TOST 等效性检验目前支持 2 组间的均值对比")
  }

  g1_vals <- sub_df[[dv]][group_factor == levels_name[1]]
  g2_vals <- sub_df[[dv]][group_factor == levels_name[2]]

  m1 <- mean(g1_vals); s1 <- sd(g1_vals); n1 <- length(g1_vals)
  m2 <- mean(g2_vals); s2 <- sd(g2_vals); n2 <- length(g2_vals)

  diff_m <- m1 - m2
  if (n1 < 2L || n2 < 2L) stop("TOST_INSUFFICIENT_SAMPLE", call. = FALSE)
  if (!is.finite(low_eqbound) || !is.finite(high_eqbound) || low_eqbound >= high_eqbound) {
    stop("TOST_INVALID_BOUNDS", call. = FALSE)
  }
  if (!is.finite(alpha) || alpha <= 0 || alpha >= 1) stop("TOST_INVALID_ALPHA", call. = FALSE)

  s_pooled <- sqrt(((n1 - 1) * s1^2 + (n2 - 1) * s2^2) / (n1 + n2 - 2))
  if (identical(variance_method, "welch")) {
    component_1 <- s1^2 / n1; component_2 <- s2^2 / n2
    se_diff <- sqrt(component_1 + component_2)
    df <- (component_1 + component_2)^2 / (component_1^2 / (n1 - 1) + component_2^2 / (n2 - 1))
  } else if (identical(variance_method, "student")) {
    se_diff <- s_pooled * sqrt(1 / n1 + 1 / n2)
    df <- n1 + n2 - 2
  } else {
    stop("TOST_VARIANCE_METHOD_NOT_SUPPORTED", call. = FALSE)
  }
  if (!is.finite(se_diff) || se_diff <= 0 || !is.finite(df) || df <= 0) {
    stop("TOST_STANDARD_ERROR_UNAVAILABLE", call. = FALSE)
  }

  cohens_d <- diff_m / s_pooled

  # TOST One-sided test 1: test if difference > low_eqbound
  t1 <- (diff_m - low_eqbound) / se_diff
  p1 <- 1 - pt(t1, df = df)

  # TOST One-sided test 2: test if difference < high_eqbound
  t2 <- (diff_m - high_eqbound) / se_diff
  p2 <- pt(t2, df = df)

  p_tost <- max(p1, p2)
  equivalent <- p_tost < alpha

  list(
    available = TRUE,
    dv = dv,
    groups = as.list(levels_name),
    meanDifference = finite_number(diff_m),
    cohensD = finite_number(cohens_d),
    lowEquivalenceBound = finite_number(low_eqbound),
    highEquivalenceBound = finite_number(high_eqbound),
    t1 = finite_number(t1),
    p1 = finite_number(p1),
    t2 = finite_number(t2),
    p2 = finite_number(p2),
    pTOST = finite_number(p_tost),
    standardError = finite_number(se_diff),
    degreesOfFreedom = finite_number(df),
    varianceMethod = variance_method,
    equivalent = equivalent
  )
}

apply_multiplicity_correction <- function(p_values, method = "holm") {
  valid_methods <- c("holm", "hochberg", "hommel", "bonferroni", "BH", "BY", "fdr", "none")
  if (!method %in% valid_methods) {
    method <- "holm"
  }

  p_vec <- as.numeric(p_values)
  adj_p <- p.adjust(p_vec, method = method)

  res <- lapply(seq_along(p_vec), function(i) {
    list(
      index = as.integer(i),
      originalPValue = finite_number(p_vec[i]),
      adjustedPValue = finite_number(adj_p[i]),
      significantAfterCorrection = adj_p[i] < 0.05,
      method = method
    )
  })

  list(
    available = TRUE,
    method = method,
    pValues = res
  )
}
