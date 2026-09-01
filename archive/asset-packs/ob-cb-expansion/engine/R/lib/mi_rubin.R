# ResearchPath R Engine - Multiple Imputation Rubin Pooling & D1-D3 Testing (WP-MI-02 & WP-MI-03)

pool_rubin_estimates <- function(estimates, standard_errors, m_df = NULL) {
  m <- length(estimates)
  if (m < 2) {
    stop("Rubin 规则汇合需要至少 2 个插补数据集的结果")
  }
  if (length(standard_errors) != m || any(!is.finite(estimates)) || any(!is.finite(standard_errors)) || any(standard_errors < 0)) {
    stop("Rubin 规则汇合的估计值和标准误必须是等长有限数值")
  }

  q_bar <- mean(estimates)
  u_bar <- mean(standard_errors^2)
  b_var <- var(estimates)

  t_var <- u_bar + (1 + 1 / m) * b_var
  se_pooled <- sqrt(t_var)

  # Barnard-Rubin degrees of freedom adjustment
  df_com <- if (!is.null(m_df)) mean(m_df) else Inf
  riv <- if (u_bar > 0) (1 + 1 / m) * b_var / u_bar else if (b_var > 0) Inf else 0
  df_old <- if (is.finite(riv)) (m - 1) * (1 + 1 / riv)^2 else m - 1
  gamma <- if (t_var > 0) (1 + 1 / m) * b_var / t_var else 0
  df_obs <- if (is.finite(df_com)) ((df_com + 1) / (df_com + 3)) * df_com * (1 - gamma) else Inf
  # The algebraic product form produces Inf / Inf when the between-imputation
  # variance is exactly zero.  In that limiting case the observed-data df is
  # the Barnard--Rubin limit; retain it rather than serialising NaN/null.
  nu <- if (is.infinite(df_old) && is.finite(df_obs)) {
    df_obs
  } else if (is.finite(df_obs)) {
    (df_old * df_obs) / (df_old + df_obs)
  } else {
    df_old
  }
  fmi <- if (is.finite(riv)) (riv + 2 / (df_old + 3)) / (riv + 1) else 1

  t_stat <- if (se_pooled > 0) q_bar / se_pooled else 0
  p_val <- if (se_pooled > 0) 2 * (1 - pt(abs(t_stat), df = nu)) else if (q_bar == 0) 1 else 0

  margin <- if (se_pooled > 0) qt(0.975, df = nu) * se_pooled else 0

  list(
    m = as.integer(m),
    pooledEstimate = finite_number(q_bar),
    pooledSE = finite_number(se_pooled),
    withinVariance = finite_number(u_bar),
    betweenVariance = finite_number(b_var),
    totalVariance = finite_number(t_var),
    degreesOfFreedom = finite_number(nu),
    tStatistic = finite_number(t_stat),
    pValue = finite_number(p_val),
    ciLower = finite_number(q_bar - margin),
    ciUpper = finite_number(q_bar + margin),
    RIV = finite_number(riv),
    FMI = finite_number(fmi)
  )
}

test_d1_d3_multivariate <- function(estimates_list, vcov_list) {
  m <- length(estimates_list)
  if (m < 2 || length(vcov_list) != m) stop("D1 检验需要至少 2 个等长插补结果和协方差矩阵")
  k <- length(estimates_list[[1]])
  if (k < 1 || any(vapply(estimates_list, length, integer(1)) != k)) stop("D1 检验的估计向量长度必须一致")

  q_bar <- colMeans(do.call(rbind, estimates_list))
  u_bar <- Reduce("+", vcov_list) / m

  b_mat <- matrix(0, nrow = k, ncol = k)
  for (i in 1:m) {
    diff_vec <- estimates_list[[i]] - q_bar
    b_mat <- b_mat + outer(diff_vec, diff_vec)
  }
  b_mat <- b_mat / (m - 1)

  u_inverse <- tryCatch(solve(u_bar), error = function(e) NULL)
  if (is.null(u_inverse)) stop("D1 检验的平均协方差矩阵不可逆")
  r_val <- (1 + 1 / m) * sum(diag(b_mat %*% u_inverse)) / k
  t_mat <- u_bar * (1 + r_val)

  t_inverse <- tryCatch(solve(t_mat), error = function(e) NULL)
  if (is.null(t_inverse)) stop("D1 检验的总协方差矩阵不可逆")
  d1_stat <- as.numeric(t(q_bar) %*% t_inverse %*% q_bar / k)
  df2 <- if (r_val > 0) 4 + (k * (m - 1) - 4) * (1 + (1 - 2 / (k * (m - 1))) / r_val)^2 else Inf
  p_val <- 1 - pf(d1_stat, df1 = k, df2 = df2)

  list(
    available = TRUE,
    method = "D1 Multivariate Wald Test",
    d1Statistic = finite_number(d1_stat),
    df1 = as.integer(k),
    df2 = finite_number(df2),
    pValue = finite_number(p_val),
    rValue = finite_number(r_val)
  )
}
