fit_hierarchical_regression <- function(
  data, options, label_for, confidence_level = 0.95,
  multiplicity_family_id = "cross_sectional_inference"
) {
  outcome_id <- options$outcomeVariableId
  controls <- unlist(options$controlVariableIds)
  predictors <- unlist(options$predictorVariableIds)
  all_ids <- unique(c(outcome_id, controls, predictors))
  regression_source <- data[, all_ids, drop = FALSE]
  regression_missing_counts <- vapply(regression_source, function(column) sum(is.na(column)), integer(1))
  regression_data <- regression_source
  regression_data <- regression_data[complete.cases(regression_data), , drop = FALSE]
  terms1 <- if (length(controls) > 0) controls else "1"
  terms2 <- if (length(c(controls, predictors)) > 0) c(controls, predictors) else "1"
  block1_formula <- reformulate(terms1, response = outcome_id)
  block2_formula <- reformulate(terms2, response = outcome_id)
  requested_parameter_count <- 1L + length(controls) + length(predictors)
  underdetermined <- nrow(regression_data) <= requested_parameter_count
  sample_flow <- list(
    original = as.integer(nrow(data)),
    included = as.integer(nrow(regression_data)),
    excluded = as.integer(nrow(data) - nrow(regression_data)),
    missingRows = as.integer(nrow(data) - nrow(regression_data)),
    finalN = as.integer(nrow(regression_data)),
    missingMethod = "regression complete cases",
    variableMissingCounts = as.list(regression_missing_counts)
  )
  if (underdetermined) {
    hc3_unavailable <- researchpath_hc3_failure(
      "HC3_NOT_RUN_UNDERDETERMINED",
      rank = NA_integer_,
      parameter_count = requested_parameter_count
    )
    empty_block <- function(block_number, formula_obj) list(
      block = block_number,
      formula = paste(deparse(formula_obj), collapse = " "),
      rSquared = NA_real_, adjustedRSquared = NA_real_, coefficients = list()
    )
    return(list(
      outcomeVariableId = outcome_id, outcomeLabel = label_for(outcome_id), n = nrow(regression_data),
      controls = as.list(controls), predictors = as.list(predictors), underdetermined = TRUE,
      estimand = "adjusted mean association per one-unit predictor change (OLS)",
      primaryAnalysis = list(
        method = "ordinary OLS",
        role = "primary",
        confidenceLevel = confidence_level,
        selectionRule = "预先声明普通 OLS 为主分析；不根据 p 值自动切换。"
      ),
      publicationEligible = FALSE,
      requiresManualReview = TRUE,
      publicationEligibilityReasons = list("REGRESSION_UNDERDETERMINED"),
      sampleFlow = sample_flow,
      blocks = list(empty_block(1L, block1_formula), empty_block(2L, block2_formula)),
      change = list(deltaRSquared = NA_real_, statistic = NA_real_, df1 = NA_real_, df2 = NA_real_, pValue = NA_real_),
      robustness = list(
        hc3Execution = c(
          researchpath_hc3_execution_metadata(hc3_unavailable),
          list(
            requested = "HC3", executed = "not_run",
            confidenceLevel = confidence_level,
            leveragePolicy = "exact hat values; no clipping; leverage effectively equal to one makes HC3 unavailable"
          )
        ),
        standardErrorComparison = list(), influence = list(
          cookDistanceCutoff = NA_real_, leverageCutoff = NA_real_, influentialCount = 0L,
          retainedCount = nrow(regression_data), maximumCookDistance = NA_real_, maximumLeverage = NA_real_,
          rule = "回归欠定时不进行影响点驱动的主模型重估"
        ),
        coefficientStability = list()
      ),
      relativeImportance = list(available = FALSE, reason = "REGRESSION_UNDERDETERMINED")
    ))
  }
  block1 <- lm(block1_formula, data = regression_data)
  block2 <- lm(block2_formula, data = regression_data)
  unadjusted <- lm(reformulate(predictors, response = outcome_id), data = regression_data)
  summaries <- list(summary(block1), summary(block2))
  comparison <- tryCatch(anova(block1, block2), error = function(e) NULL)
  robustness <- regression_sensitivity_report(block2, unadjusted, label_for, confidence_level)
  hc3_unavailable <- !isTRUE(robustness$hc3Execution$available)
  list(
    outcomeVariableId = outcome_id, outcomeLabel = label_for(outcome_id), n = nrow(regression_data),
    controls = as.list(controls), predictors = as.list(predictors),
    underdetermined = underdetermined,
    estimand = "adjusted mean association per one-unit predictor change (OLS)",
    primaryAnalysis = list(
      method = "ordinary OLS",
      role = "primary",
      confidenceLevel = confidence_level,
      selectionRule = "预先声明普通 OLS 为主分析；不根据 p 值自动切换。"
    ),
    publicationEligible = !hc3_unavailable,
    requiresManualReview = hc3_unavailable,
    publicationEligibilityReasons = if (hc3_unavailable) list("HC3_UNAVAILABLE") else list(),
    sampleFlow = sample_flow,
    multiplicityFamilyId = multiplicity_family_id,
    blocks = lapply(seq_len(2), function(index) list(
      block = index, formula = paste(deparse(formula(list(block1, block2)[[index]])), collapse = " "),
      rSquared = if (underdetermined) NA_real_ else finite_number(summaries[[index]]$r.squared),
      adjustedRSquared = if (underdetermined) NA_real_ else finite_number(summaries[[index]]$adj.r.squared),
      coefficients = coefficient_rows(list(block1, block2)[[index]], label_for, confidence_level = confidence_level)
    )),
    change = if (underdetermined || is.null(comparison)) list(
      deltaRSquared = NA_real_, statistic = NA_real_, df1 = NA_real_, df2 = NA_real_, pValue = NA_real_
    ) else list(
      deltaRSquared = finite_number(summaries[[2]]$r.squared - summaries[[1]]$r.squared),
      statistic = finite_number(comparison$F[2]), df1 = finite_number(comparison$Df[2]),
      df2 = finite_number(df.residual(block2)), pValue = finite_number(comparison$`Pr(>F)`[2])
    ),
    robustness = robustness,
    relativeImportance = if (is.null(options$procedure) || identical(options$procedure, "relative_importance")) fit_relative_importance(
      regression_data, outcome_id, predictors, controls, label_for
    ) else NULL
  )
}
