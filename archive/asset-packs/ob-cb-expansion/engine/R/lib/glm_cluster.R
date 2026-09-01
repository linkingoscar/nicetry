# ResearchPath R Engine - GLM, Cluster-Robust SE & ITT Analysis (WP-EXP-04)

fit_glm_cluster_robust <- function(data, dv, predictors, family_name = "binomial", cluster_var = NULL) {
  if (!dv %in% colnames(data)) {
    stop(paste("因变量不存在:", dv))
  }

  valid_preds <- predictors[predictors %in% colnames(data)]
  if (length(valid_preds) == 0) {
    stop("未提供有效自变量")
  }

  formula_str <- paste(dv, "~", paste(valid_preds, collapse = " + "))

  family_obj <- switch(family_name,
    "binomial" = binomial(link = "logit"),
    "poisson" = poisson(link = "log"),
    "gaussian" = gaussian(link = "identity"),
    binomial(link = "logit")
  )

  fit <- glm(as.formula(formula_str), data = data, family = family_obj)
  fit_s <- summary(fit)

  coefs <- fit_s$coefficients
  terms <- rownames(coefs)

  # Cluster-robust standard error approximation if cluster_var is specified
  if (!is.null(cluster_var) && cluster_var %in% colnames(data)) {
    cluster_vec <- data[[cluster_var]]
    n_clusters <- length(unique(na.omit(cluster_vec)))

    # Sandwich estimator approximation for cluster robust SE
    u_mat <- residuals(fit, type = "working") * model.matrix(fit)
    aggr_u <- aggregate(u_mat, by = list(cluster_vec), FUN = sum, na.rm = TRUE)[, -1]
    bread <- vcov(fit) * nrow(data)
    meat <- cov(aggr_u) * (n_clusters / (n_clusters - 1))
    vcov_cr <- bread %*% meat %*% bread / nrow(data)

    se_vec <- sqrt(diag(vcov_cr))
    z_stat <- coefs[, "Estimate"] / se_vec
    p_val <- 2 * (1 - pnorm(abs(z_stat)))

    coef_table <- data.frame(
      Term = terms,
      Estimate = coefs[, "Estimate"],
      StdError = se_vec,
      zValue = z_stat,
      pValue = p_val
    )
  } else {
    coef_table <- data.frame(
      Term = terms,
      Estimate = coefs[, "Estimate"],
      StdError = coefs[, 2],
      zValue = coefs[, 3],
      pValue = coefs[, 4]
    )
  }

  coef_results <- lapply(1:nrow(coef_table), function(i) {
    est <- as.numeric(coef_table$Estimate[i])
    se <- as.numeric(coef_table$StdError[i])
    p <- as.numeric(coef_table$pValue[i])
    exp_est <- if (family_name %in% c("binomial", "poisson")) round(exp(est), 4) else NULL

    list(
      term = as.character(coef_table$Term[i]),
      estimate = round(est, 4),
      standardError = round(se, 4),
      statistic = round(as.numeric(coef_table$zValue[i]), 4),
      pValue = round(p, 6),
      oddsRatioOrRiskRatio = exp_est,
      ciLower = round(est - 1.96 * se, 4),
      ciUpper = round(est + 1.96 * se, 4)
    )
  })

  list(
    family = family_name,
    clusterVariable = cluster_var,
    clusterRobustUsed = !is.null(cluster_var) && cluster_var %in% colnames(data),
    aic = round(AIC(fit), 2),
    deviance = round(fit$deviance, 2),
    coefficients = coef_results
  )
}
