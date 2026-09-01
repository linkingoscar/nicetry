# ResearchPath R Engine - Repeated & Mixed ANOVA Depth (WP-EXP-03)

evaluate_sphericity_and_correction <- function(data, outcome_cols) {
  if (length(outcome_cols) < 3) {
    return(list(
      sphericityApplicable = FALSE,
      mauchlyW = 1.0,
      pValue = 1.0,
      sphericityViolated = FALSE,
      greenhouseGeisserEpsilon = 1.0,
      huynhFeldtEpsilon = 1.0
    ))
  }

  mat <- as.matrix(data[, outcome_cols])
  mat <- mat[complete.cases(mat), ]
  n <- nrow(mat)
  k <- ncol(mat)

  cov_mat <- cov(mat)

  # Orthogonal contrast matrix for repeated measures
  C_mat <- contr.poly(k)
  S_mat <- t(C_mat) %*% cov_mat %*% C_mat

  p_dim <- k - 1
  tr_S <- sum(diag(S_mat))
  det_S <- det(S_mat)

  w_stat <- det_S / ((tr_S / p_dim)^p_dim)
  if (is.na(w_stat) || w_stat <= 0) w_stat <- 1.0

  # Greenhouse-Geisser epsilon calculation
  tr_S2 <- sum(S_mat * S_mat)
  gg_eps <- (tr_S^2) / (p_dim * tr_S2)
  if (is.na(gg_eps)) gg_eps <- 1.0
  gg_eps <- min(1.0, max(1 / p_dim, gg_eps))

  # Huynh-Feldt epsilon calculation
  hf_eps <- (n * p_dim * gg_eps - 2) / (p_dim * (n - 1 - p_dim * gg_eps))
  if (is.na(hf_eps)) hf_eps <- 1.0
  hf_eps <- min(1.0, max(gg_eps, hf_eps))

  # Approximate Chi-Square for Mauchly
  df <- (p_dim * (p_dim + 1)) / 2 - 1
  chi_sq <- -(n - 1 - (2 * p_dim + 1 + 2 / p_dim) / 6) * log(w_stat)
  p_val <- if (df > 0 && chi_sq > 0) 1 - pchisq(chi_sq, df = df) else 1.0

  list(
    sphericityApplicable = TRUE,
    mauchlyW = finite_number(w_stat),
    pValue = finite_number(p_val),
    sphericityViolated = p_val < 0.05,
    greenhouseGeisserEpsilon = finite_number(gg_eps),
    huynhFeldtEpsilon = finite_number(hf_eps)
  )
}

# ---------------------------------------------------------------------------
# RM-ANOVA & Mixed Design Execution (WP-CORE-E-03)
# ---------------------------------------------------------------------------

fit_repeated_measures_anova <- function(data, outcome_cols, between_factor = NULL, confidence_level = 0.95) {
  if (length(outcome_cols) < 2) {
    stop("REPEATED_MEASURES_REQUIRES_MULTIPLE_MEASURES: 重复测量分析至少需要两个时间点/条件")
  }

  valid_df <- data[complete.cases(data[, outcome_cols, drop = FALSE]), , drop = FALSE]
  n <- nrow(valid_df)
  k <- length(outcome_cols)
  if (n < 4) {
    stop("REPEATED_MEASURES_INSUFFICIENT_OBSERVATIONS: 样本量不足以估计重复测量方差分析")
  }

  sphericity_info <- evaluate_sphericity_and_correction(valid_df, outcome_cols)

  # Reshape wide to long for model fitting
  long_list <- lapply(seq_along(outcome_cols), function(idx) {
    col <- outcome_cols[idx]
    sub <- data.frame(
      subject = seq_len(n),
      time = col,
      outcome = valid_df[[col]]
    )
    if (!is.null(between_factor) && between_factor %in% names(valid_df)) {
      sub[[between_factor]] <- valid_df[[between_factor]]
    }
    sub
  })
  long_df <- do.call(rbind, long_list)
  long_df$time <- factor(long_df$time, levels = outcome_cols)
  long_df$subject <- factor(long_df$subject)

  # Model formula
  formula_str <- if (!is.null(between_factor)) {
    long_df[[between_factor]] <- factor(long_df[[between_factor]])
    paste("outcome ~ time *", between_factor, "+ Error(subject/time)")
  } else {
    "outcome ~ time + Error(subject/time)"
  }

  fit <- aov(as.formula(formula_str), data = long_df)
  fit_sum <- summary(fit)

  # Extract ANOVA table from summary
  eff_row <- fit_sum[["Error: subject:time"]][[1]]["time", ]
  err_row <- fit_sum[["Error: subject:time"]][[1]]["Residuals", ]

  df1 <- eff_row[["Df"]]
  df2 <- err_row[["Df"]]
  f_stat <- eff_row[["F value"]]
  p_orig <- eff_row[["Pr(>F)"]]

  gg_eps <- sphericity_info$greenhouseGeisserEpsilon
  hf_eps <- sphericity_info$huynhFeldtEpsilon

  df1_gg <- df1 * gg_eps
  df2_gg <- df2 * gg_eps
  p_gg <- pf(f_stat, df1_gg, df2_gg, lower.tail = FALSE)

  df1_hf <- df1 * hf_eps
  df2_hf <- df2 * hf_eps
  p_hf <- pf(f_stat, df1_hf, df2_hf, lower.tail = FALSE)

  # Calculate EMMs across repeated conditions
  means <- colMeans(valid_df[, outcome_cols], na.rm = TRUE)
  sds <- apply(valid_df[, outcome_cols], 2, sd, na.rm = TRUE)
  se_val <- sqrt(err_row[["Mean Sq"]] / n)
  crit <- qt(1 - (1 - confidence_level) / 2, df = df2)

  emms <- lapply(seq_along(outcome_cols), function(idx) {
    col <- outcome_cols[idx]
    m_val <- means[[col]]
    list(
      condition = col,
      n = as.integer(n),
      mean = finite_number(m_val),
      standardError = finite_number(se_val),
      ciLower = finite_number(m_val - crit * se_val),
      ciUpper = finite_number(m_val + crit * se_val)
    )
  })

  list(
    available = TRUE,
    sampleSize = as.integer(n),
    repeatedConditionsCount = as.integer(k),
    sphericity = sphericity_info,
    anovaTable = list(
      uncorrected = list(
        effect = "time",
        fStatistic = finite_number(f_stat),
        df1 = as.integer(df1),
        df2 = as.integer(df2),
        pValue = finite_number(p_orig)
      ),
      greenhouseGeisser = list(
        epsilon = finite_number(gg_eps),
        df1 = finite_number(df1_gg),
        df2 = finite_number(df2_gg),
        pValue = finite_number(p_gg)
      ),
      huynhFeldt = list(
        epsilon = finite_number(hf_eps),
        df1 = finite_number(df1_hf),
        df2 = finite_number(df2_hf),
        pValue = finite_number(p_hf)
      )
    ),
    estimatedMarginalMeans = emms
  )
}

