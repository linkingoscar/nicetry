# ResearchPath R Engine - Multilevel Advanced Modeling & Multilevel Mediation (WP-MLM-01~04)

fit_multilevel_advanced <- function(data, dv, level1_vars, level2_vars, cluster_var, random_slopes = NULL) {
  suppressPackageStartupMessages(library(lme4))
  suppressPackageStartupMessages(library(lmerTest))

  if (!dv %in% colnames(data) || !cluster_var %in% colnames(data)) {
    stop("因变量或聚类变量不存在")
  }

  all_preds <- unique(c(level1_vars, level2_vars))
  valid_preds <- all_preds[all_preds %in% colnames(data)]

  # Random effects syntax construction
  if (!is.null(random_slopes) && length(random_slopes) > 0) {
    rs_vars <- random_slopes[random_slopes %in% colnames(data)]
    re_str <- paste0("(1 + ", paste(rs_vars, collapse = " + "), " | ", cluster_var, ")")
  } else {
    re_str <- paste0("(1 | ", cluster_var, ")")
  }

  formula_str <- paste(dv, "~", paste(valid_preds, collapse = " + "), "+", re_str)
  fit <- lmer(as.formula(formula_str), data = data)
  fit_s <- summary(fit)

  coef_mat <- fit_s$coefficients
  fixed_effects <- lapply(rownames(coef_mat), function(name) {
    list(
      term = name,
      estimate = round(as.numeric(coef_mat[name, "Estimate"]), 4),
      standardError = round(as.numeric(coef_mat[name, "Std. Error"]), 4),
      tStatistic = round(as.numeric(coef_mat[name, "t value"]), 4),
      df = round(as.numeric(coef_mat[name, "df"]), 2),
      pValue = round(as.numeric(coef_mat[name, "Pr(>|t|)"]), 6)
    )
  })

  var_comp <- as.data.frame(VarCorr(fit))
  variance_components <- lapply(1:nrow(var_comp), function(i) {
    list(
      group = as.character(var_comp$grp[i]),
      var1 = as.character(var_comp$var1[i]),
      var2 = as.character(var_comp$var2[i]),
      variance = round(as.numeric(var_comp$vcov[i]), 4),
      sd = round(as.numeric(var_comp$sdcor[i]), 4)
    )
  })

  list(
    dv = dv,
    clusterVariable = cluster_var,
    formula = formula_str,
    aic = round(AIC(fit), 2),
    bic = round(BIC(fit), 2),
    fixedEffects = fixed_effects,
    varianceComponents = variance_components
  )
}
