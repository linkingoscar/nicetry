# ResearchPath R Engine - Specification Curve Analysis (WP-ROBUST-01)

run_specification_curve <- function(data, dv, iv, candidate_covariates = NULL) {
  if (!dv %in% colnames(data) || !iv %in% colnames(data)) {
    stop("指定的因变量或自变量不存在")
  }

  cov_list <- list()
  if (!is.null(candidate_covariates) && length(candidate_covariates) > 0) {
    valid_covs <- candidate_covariates[candidate_covariates %in% colnames(data)]
    # Generate all subsets of covariates
    cov_combos <- unlist(lapply(0:length(valid_covs), function(n) {
      combn(valid_covs, n, simplify = FALSE)
    }), recursive = FALSE)
  } else {
    cov_combos <- list(character(0))
  }

  specifications <- lapply(seq_along(cov_combos), function(idx) {
    covs <- cov_combos[[idx]]
    formula_str <- if (length(covs) > 0) {
      paste(dv, "~", iv, "+", paste(covs, collapse = " + "))
    } else {
      paste(dv, "~", iv)
    }

    fit <- lm(as.formula(formula_str), data = data)
    fit_s <- summary(fit)

    coef_row <- fit_s$coefficients[iv, ]
    est <- coef_row["Estimate"]
    se <- coef_row["Std. Error"]
    p_val <- coef_row["Pr(>|t|)"]

    list(
      specId = idx,
      covariates = covs,
      estimate = round(as.numeric(est), 4),
      standardError = round(as.numeric(se), 4),
      pValue = round(as.numeric(p_val), 6),
      significant = p_val < 0.05
    )
  })

  estimates <- sapply(specifications, function(s) s$estimate)
  p_values <- sapply(specifications, function(s) s$pValue)

  list(
    dv = dv,
    iv = iv,
    totalSpecifications = length(specifications),
    medianEstimate = round(median(estimates), 4),
    iqrEstimate = round(IQR(estimates), 4),
    minEstimate = round(min(estimates), 4),
    maxEstimate = round(max(estimates), 4),
    significantRatio = round(mean(p_values < 0.05), 4),
    specifications = specifications
  )
}
