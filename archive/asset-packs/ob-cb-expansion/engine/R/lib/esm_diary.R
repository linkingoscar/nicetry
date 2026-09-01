# ResearchPath R Engine - Experience Sampling Method (ESM) & Daily Diary (WP-ESM-01)

fit_esm_diary_model <- function(data, dv, iv, id_var, time_var = NULL) {
  suppressPackageStartupMessages(library(lme4))

  if (!all(c(dv, iv, id_var) %in% colnames(data))) {
    stop("指定的变量在数据集中不存在")
  }

  sub_df <- data[!is.na(data[[dv]]) & !is.na(data[[iv]]) & !is.na(data[[id_var]]), ]

  # Mundlak Within-Between Centering
  between_iv <- tapply(sub_df[[iv]], sub_df[[id_var]], mean, na.rm = TRUE)
  sub_df$iv_between <- between_iv[as.character(sub_df[[id_var]])]
  sub_df$iv_within <- sub_df[[iv]] - sub_df$iv_between

  formula_str <- paste(dv, "~ iv_within + iv_between + (1 + iv_within |", id_var, ")")
  fit <- lmer(as.formula(formula_str), data = sub_df)
  fit_s <- summary(fit)

  coef_mat <- fit_s$coefficients

  within_effect <- list(
    term = "iv_within (Person-centered / Within effect)",
    estimate = round(as.numeric(coef_mat["iv_within", "Estimate"]), 4),
    standardError = round(as.numeric(coef_mat["iv_within", "Std. Error"]), 4),
    tStatistic = round(as.numeric(coef_mat["iv_within", "t value"]), 4),
    pValue = round(as.numeric(coef_mat["iv_within", "Pr(>|t|)"]), 6)
  )

  between_effect <- list(
    term = "iv_between (Person-mean / Between effect)",
    estimate = round(as.numeric(coef_mat["iv_between", "Estimate"]), 4),
    standardError = round(as.numeric(coef_mat["iv_between", "Std. Error"]), 4),
    tStatistic = round(as.numeric(coef_mat["iv_between", "t value"]), 4),
    pValue = round(as.numeric(coef_mat["iv_between", "Pr(>|t|)"]), 6)
  )

  list(
    design = "Experience Sampling / Daily Diary Study",
    dv = dv,
    iv = iv,
    subjectVariable = id_var,
    timeVariable = time_var,
    mundlakCentering = TRUE,
    withinPersonEffect = within_effect,
    betweenPersonEffect = between_effect
  )
}
