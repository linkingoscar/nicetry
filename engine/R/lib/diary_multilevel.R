.this_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
if (is.null(.this_dir) || nchar(.this_dir) == 0) .this_dir <- "."
if (file.exists(file.path(.this_dir, "diary_utils.R"))) {
  source(file.path(.this_dir, "diary_utils.R"))
  source(file.path(.this_dir, "centering_utils.R"))
  source(file.path(.this_dir, "time_series_utils.R"))
}
diary_finite <- ensure_finite
diary_result_scenario <- ensure_result_scenario

diary_prepare <- validate_diary_data

diary_center_predictor <- center_predictor
diary_centering_manifest <- centering_manifest

diary_time_trend_test <- function(fit, time_terms, time_protocol) {
  if (length(time_terms) == 0L) return(NULL)
  coefficients <- if (inherits(fit, "merMod")) {
    lme4::fixef(fit)
  } else if (inherits(fit, "glmmTMB")) {
    glmmTMB::fixef(fit)$cond
  } else if (inherits(fit, "lme")) {
    nlme::fixef(fit)
  } else {
    tryCatch(stats::coef(fit), error = function(error) NULL)
  }
  covariance <- tryCatch(
    if (inherits(fit, "glmmTMB")) {
      as.matrix(stats::vcov(fit)$cond)
    } else {
      as.matrix(stats::vcov(fit))
    },
    error = function(error) NULL
  )
  available <- intersect(time_terms, names(coefficients))
  if (is.null(covariance) || length(available) == 0L) return(NULL)
  beta <- coefficients[available]
  beta_covariance <- covariance[available, available, drop = FALSE]
  statistic <- tryCatch(
    as.numeric(t(beta) %*% solve(beta_covariance, beta)),
    error = function(error) NA_real_
  )
  quadratic <- time_protocol$quadraticTerm
  linear <- time_protocol$linearTerm
  turning_point_centered <- if (
    !is.null(quadratic) &&
    quadratic %in% names(coefficients) &&
    linear %in% names(coefficients) &&
    is.finite(coefficients[[quadratic]]) &&
    abs(coefficients[[quadratic]]) > 1e-12
  ) {
    -coefficients[[linear]] / (2 * coefficients[[quadratic]])
  } else {
    NA_real_
  }
  turning_point <- if (is.finite(turning_point_centered)) {
    turning_point_centered + time_protocol$originValue
  } else {
    NA_real_
  }
  list(
    terms = as.list(available),
    statistic = ensure_finite(statistic),
    degreesOfFreedom = length(available),
    pValue = if (is.finite(statistic)) {
      ensure_finite(stats::pchisq(statistic, df = length(available), lower.tail = FALSE))
    } else {
      NULL
    },
    method = "Joint Wald chi-square test",
    originStrategy = time_protocol$originStrategy,
    originValue = time_protocol$originValue,
    linearSlopeAtOrigin = if (linear %in% names(coefficients)) {
      ensure_finite(coefficients[[linear]])
    } else {
      NULL
    },
    quadraticCoefficient = if (!is.null(quadratic) && quadratic %in% names(coefficients)) {
      ensure_finite(coefficients[[quadratic]])
    } else {
      NULL
    },
    turningPoint = ensure_finite(turning_point),
    turningPointInObservedRange = if (is.finite(turning_point)) {
      turning_point >= time_protocol$observedMinimum &&
        turning_point <= time_protocol$observedMaximum
    } else {
      NULL
    }
  )
}

diary_lmer_coefficients <- function(fit, confidence_level, label_for) {
  coefficients <- as.data.frame(coef(summary(fit)))
  coefficients$term <- rownames(coefficients)
  rownames(coefficients) <- NULL
  critical <- qt(
    1 - (1 - confidence_level) / 2,
    df = pmax(1, suppressWarnings(as.numeric(coefficients$df)))
  )
  lapply(seq_len(nrow(coefficients)), function(index) {
    list(
      term = coefficients$term[[index]],
      label = label_for(coefficients$term[[index]]),
      estimate = ensure_finite(coefficients$Estimate[[index]]),
      standardError = ensure_finite(coefficients$`Std. Error`[[index]]),
      degreesOfFreedom = ensure_finite(coefficients$df[[index]]),
      statistic = ensure_finite(coefficients$`t value`[[index]]),
      pValue = ensure_finite(coefficients$`Pr(>|t|)`[[index]]),
      lower = ensure_finite(coefficients$Estimate[[index]] - critical[[index]] * coefficients$`Std. Error`[[index]]),
      upper = ensure_finite(coefficients$Estimate[[index]] + critical[[index]] * coefficients$`Std. Error`[[index]])
    )
  })
}

fit_diary_lmm <- function(data, spec, label_for, confidence_level) {
  suppressPackageStartupMessages(library(lme4))
  suppressPackageStartupMessages(library(lmerTest))
  centered <- center_predictor(data, spec)
  temporal <- diary_temporal_design(centered$data, spec, centered)
  data <- temporal$data
  fixed <- unique(c(
    temporal$predictorTerms,
    centered$between,
    temporal$timeTerms,
    unlist(spec$level2CovariateIds),
    unlist(spec$controlVariableIds)
  ))
  fixed <- fixed[!is.na(fixed) & nzchar(fixed)]
  data <- data[complete.cases(data[, unique(c(
    spec$outcomeVariableId, spec$subjectVariableId, fixed
  )), drop = FALSE]), , drop = FALSE]
  if (nrow(data) < 10L) stop("DIARY_INSUFFICIENT_TEMPORAL_OBSERVATIONS")
  subject <- spec$subjectVariableId
  outcome <- spec$outcomeVariableId
  random_predictor <- if (
    identical(spec$temporalEffect, "lagged") && !is.null(temporal$laggedPredictorId)
  ) {
    temporal$laggedPredictorId
  } else {
    centered$within
  }
  random_inside <- if (isTRUE(spec$randomSlope)) {
    paste0("1 + ", random_predictor)
  } else {
    "1"
  }
  random_terms <- paste0("(", random_inside, " | ", subject, ")")
  if (identical(spec$clusterStructure, "cross_classified")) {
    random_terms <- c(
      random_terms,
      paste0("(1 | ", spec$crossClassVariableId, ")")
    )
  }
  formula <- as.formula(paste(
    outcome,
    "~",
    paste(c(fixed, random_terms), collapse = " + ")
  ))
  captured_warnings <- character(0)
  fit <- withCallingHandlers(
    lmerTest::lmer(formula, data = data, REML = TRUE),
    warning = function(warning) {
      captured_warnings <<- c(captured_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )
  convergence_messages <- unlist(fit@optinfo$conv$lme4$messages)
  singular <- lme4::isSingular(fit)
  diagnostics <- lapply(unique(c(captured_warnings, convergence_messages)), function(message) {
    list(code = "LMM_WARNING", severity = "warning", message = message)
  })
  if (singular) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "SINGULAR_FIT",
      severity = "warning",
      message = "随机效应协方差位于奇异边界；随机斜率或相关结构可能过度参数化。"
    )
  }
  variance <- as.data.frame(VarCorr(fit))
  residual_variance <- sigma(fit)^2
  intercept_row <- variance[
    variance$grp == subject & variance$var1 == "(Intercept)" & is.na(variance$var2),
    ,
    drop = FALSE
  ]
  intercept_variance <- if (nrow(intercept_row)) intercept_row$vcov[[1]] else NA_real_
  icc <- intercept_variance / (intercept_variance + residual_variance)
  r2 <- tryCatch(performance::r2(fit), error = function(error) NULL)
  list(
    available = TRUE,
    analysisType = "lmm",
    modelLabel = if (identical(spec$clusterStructure, "cross_classified")) {
      "交叉分类线性混合模型"
    } else {
      "二层线性混合模型"
    },
    sampleSize = nrow(data),
    personCount = length(unique(data[[subject]])),
    crossClassCount = if (identical(spec$clusterStructure, "cross_classified")) {
      length(unique(data[[spec$crossClassVariableId]]))
    } else {
      NULL
    },
    observationsPerPerson = list(
      minimum = min(table(data[[subject]])),
      median = unname(median(table(data[[subject]]))),
      maximum = max(table(data[[subject]]))
    ),
    formula = paste(deparse(formula), collapse = " "),
    outcomeFamily = "gaussian",
    clusterStructure = spec$clusterStructure,
    crossClassVariableId = spec$crossClassVariableId,
    centering = spec$centering,
    withinPredictorId = centered$within,
    betweenPredictorId = centered$between,
    temporalEffect = spec$temporalEffect,
    lagOrder = spec$lagOrder,
    laggedPredictorId = temporal$laggedPredictorId,
    timeGapId = temporal$timeGapId,
    crossLevelInteractionIds = as.list(temporal$interactionTerms),
    centeringProtocol = centering_manifest(spec, centered, temporal),
    timeTrendTest = diary_time_trend_test(fit, temporal$timeTerms, temporal$timeProtocol),
    fixedEffects = format_lmer_coefficients(fit, confidence_level, label_for),
    varianceComponents = lapply(seq_len(nrow(variance)), function(index) {
      list(
        group = as.character(variance$grp[[index]]),
        term = as.character(variance$var1[[index]]),
        pairedTerm = if (is.na(variance$var2[[index]])) NULL else as.character(variance$var2[[index]]),
        variance = ensure_finite(variance$vcov[[index]]),
        standardDeviation = ensure_finite(variance$sdcor[[index]])
      )
    }),
    icc = ensure_finite(icc),
    marginalRSquared = if (is.null(r2)) NULL else ensure_finite(r2$R2_marginal),
    conditionalRSquared = if (is.null(r2)) NULL else ensure_finite(r2$R2_conditional),
    residualStructure = "independent",
    ar1 = NULL,
    singular = singular,
    randomSlope = isTRUE(spec$randomSlope),
    diagnostics = diagnostics,
    validForInterpretation = !singular && length(convergence_messages) == 0L,
    provenance = list(
      engine = "R lme4/lmerTest",
      engineVersion = as.character(packageVersion("lme4")),
      degreesOfFreedomMethod = "Satterthwaite"
    )
  )
}

fit_diary_ar1 <- function(data, spec, label_for, confidence_level) {
  suppressPackageStartupMessages(library(nlme))
  centered <- center_predictor(data, spec)
  temporal <- diary_temporal_design(centered$data, spec, centered)
  data <- temporal$data
  fixed <- unique(c(
    temporal$predictorTerms,
    centered$between,
    temporal$timeTerms,
    unlist(spec$level2CovariateIds),
    unlist(spec$controlVariableIds)
  ))
  fixed <- fixed[!is.na(fixed) & nzchar(fixed)]
  data <- data[complete.cases(data[, unique(c(
    spec$outcomeVariableId, spec$subjectVariableId, spec$timeVariableId, fixed
  )), drop = FALSE]), , drop = FALSE]
  if (nrow(data) < 10L) stop("DIARY_INSUFFICIENT_TEMPORAL_OBSERVATIONS")
  fixed_formula <- reformulate(fixed, response = spec$outcomeVariableId)
  random_predictor <- if (
    identical(spec$temporalEffect, "lagged") && !is.null(temporal$laggedPredictorId)
  ) {
    temporal$laggedPredictorId
  } else {
    centered$within
  }
  random_formula <- if (isTRUE(spec$randomSlope)) {
    as.formula(paste0("~1 + ", random_predictor, "|", spec$subjectVariableId))
  } else {
    as.formula(paste0("~1|", spec$subjectVariableId))
  }
  correlation_formula <- as.formula(paste0(
    "~", spec$timeVariableId, "|", spec$subjectVariableId
  ))
  fit <- nlme::lme(
    fixed = fixed_formula,
    random = random_formula,
    correlation = nlme::corAR1(form = correlation_formula),
    data = data,
    method = "REML",
    na.action = na.omit,
    control = nlme::lmeControl(returnObject = TRUE)
  )
  coefficient_table <- as.data.frame(summary(fit)$tTable)
  coefficient_table$term <- rownames(coefficient_table)
  intervals <- intervals(fit, level = confidence_level)$fixed
  coefficients <- lapply(seq_len(nrow(coefficient_table)), function(index) {
    term <- coefficient_table$term[[index]]
    list(
      term = term,
      label = label_for(term),
      estimate = ensure_finite(coefficient_table$Value[[index]]),
      standardError = ensure_finite(coefficient_table$`Std.Error`[[index]]),
      degreesOfFreedom = ensure_finite(coefficient_table$DF[[index]]),
      statistic = ensure_finite(coefficient_table$`t-value`[[index]]),
      pValue = ensure_finite(coefficient_table$`p-value`[[index]]),
      lower = ensure_finite(intervals[term, "lower"]),
      upper = ensure_finite(intervals[term, "upper"])
    )
  })
  ar1 <- ensure_finite(coef(fit$modelStruct$corStruct, unconstrained = FALSE))
  list(
    available = TRUE,
    analysisType = "lmm",
    modelLabel = "二层线性混合模型（AR(1)）",
    sampleSize = nrow(data),
    personCount = length(unique(data[[spec$subjectVariableId]])),
    observationsPerPerson = list(
      minimum = min(table(data[[spec$subjectVariableId]])),
      median = unname(median(table(data[[spec$subjectVariableId]]))),
      maximum = max(table(data[[spec$subjectVariableId]]))
    ),
    formula = paste(deparse(fixed_formula), collapse = " "),
    centering = spec$centering,
    withinPredictorId = centered$within,
    betweenPredictorId = centered$between,
    temporalEffect = spec$temporalEffect,
    lagOrder = spec$lagOrder,
    laggedPredictorId = temporal$laggedPredictorId,
    timeGapId = temporal$timeGapId,
    crossLevelInteractionIds = as.list(temporal$interactionTerms),
    centeringProtocol = centering_manifest(spec, centered, temporal),
    timeTrendTest = diary_time_trend_test(fit, temporal$timeTerms, temporal$timeProtocol),
    fixedEffects = coefficients,
    varianceComponents = list(),
    icc = NULL,
    marginalRSquared = NULL,
    conditionalRSquared = NULL,
    residualStructure = "ar1",
    ar1 = ar1,
    singular = FALSE,
    randomSlope = isTRUE(spec$randomSlope),
    diagnostics = list(),
    validForInterpretation = TRUE,
    provenance = list(
      engine = "R nlme",
      engineVersion = as.character(packageVersion("nlme")),
      degreesOfFreedomMethod = "nlme approximate t"
    )
  )
}

fit_diary_mediation <- function(data, spec, label_for, confidence_level) {
  suppressPackageStartupMessages(library(lavaan))
  x <- spec$predictorVariableId
  m <- spec$mediatorVariableId
  y <- spec$outcomeVariableId
  subject <- spec$subjectVariableId
  level1_controls <- unlist(spec$controlVariableIds)
  level2_controls <- unlist(spec$level2CovariateIds)
  level1_m_terms <- paste(c(sprintf("aw*%s", x), level1_controls), collapse = " + ")
  level1_y_terms <- paste(c(sprintf("bw*%s", m), sprintf("cw*%s", x), level1_controls), collapse = " + ")
  level2_m_terms <- paste(c(sprintf("ab*%s", x), level2_controls), collapse = " + ")
  level2_y_terms <- paste(c(sprintf("bb*%s", m), sprintf("cb*%s", x), level2_controls), collapse = " + ")
  for (id in level2_controls) {
    stable_counts <- tapply(data[[id]], data[[subject]], function(values) length(unique(values)))
    if (any(stable_counts > 1L)) stop(paste0("LEVEL2_COVARIATE_VARIES_WITHIN_PERSON: ", id))
  }
  if (identical(spec$mediationType, "1-1-1")) {
    syntax <- paste(
      "level: 1",
      sprintf("%s ~ %s", m, level1_m_terms),
      sprintf("%s ~ %s", y, level1_y_terms),
      "indirect_within := aw*bw",
      "level: 2",
      sprintf("%s ~ %s", m, level2_m_terms),
      sprintf("%s ~ %s", y, level2_y_terms),
      "indirect_between := ab*bb",
      sep = "\n"
    )
  } else {
    stable_x <- tapply(data[[x]], data[[subject]], function(values) length(unique(values)))
    if (any(stable_x > 1L)) stop("MEDIATION_2_1_1_X_MUST_BE_LEVEL2_CONSTANT")
    level1_y_211 <- paste(c(sprintf("bw*%s", m), level1_controls), collapse = " + ")
    syntax <- paste(
      "level: 1",
      sprintf("%s ~ %s", y, level1_y_211),
      "level: 2",
      sprintf("%s ~ %s", m, level2_m_terms),
      sprintf("%s ~ %s", y, level2_y_terms),
      "indirect_between := ab*bb",
      sep = "\n"
    )
  }
  fit <- lavaan::sem(
    syntax,
    data = data,
    cluster = subject,
    estimator = "MLR",
    missing = "listwise"
  )
  if (!isTRUE(lavaan::lavInspect(fit, "converged"))) stop("MULTILEVEL_MEDIATION_NONCONVERGENCE")
  parameters <- lavaan::parameterEstimates(
    fit,
    standardized = TRUE,
    ci = TRUE,
    level = confidence_level
  )
  effects <- parameters[parameters$op == ":=", , drop = FALSE]
  path_rows <- parameters[parameters$op == "~", , drop = FALSE]
  to_rows <- function(rows) lapply(seq_len(nrow(rows)), function(index) {
    list(
      id = if (rows$op[[index]] == ":=") rows$lhs[[index]] else paste0(rows$lhs[[index]], "~", rows$rhs[[index]]),
      lhs = rows$lhs[[index]],
      rhs = if (rows$op[[index]] == ":=") NULL else rows$rhs[[index]],
      estimate = ensure_finite(rows$est[[index]]),
      standardizedEstimate = ensure_finite(rows$std.all[[index]]),
      standardError = ensure_finite(rows$se[[index]]),
      statistic = ensure_finite(rows$z[[index]]),
      pValue = ensure_finite(rows$pvalue[[index]]),
      lower = ensure_finite(rows$ci.lower[[index]]),
      upper = ensure_finite(rows$ci.upper[[index]])
    )
  })
  post_check <- isTRUE(lavaan::lavInspect(fit, "post.check"))
  list(
    available = TRUE,
    analysisType = "mediation",
    modelLabel = paste0(spec$mediationType, " 多层中介"),
    mediationType = spec$mediationType,
    sampleSize = nrow(data),
    personCount = length(unique(data[[subject]])),
    paths = to_rows(path_rows),
    indirectEffects = to_rows(effects),
    fitIndices = panel_fit_indices(fit),
    diagnostics = if (post_check) list() else list(list(
      code = "POST_ESTIMATION_INVALID",
      severity = "warning",
      message = "多层 SEM 后估计检查未通过，结果仅供诊断。"
    )),
    validForInterpretation = post_check,
    methodNotice = "间接效应由二层结构方程模型同时估计；within-person 与 between-person 效应必须分别解释。",
    provenance = list(
      engine = "R lavaan multilevel SEM",
      engineVersion = as.character(packageVersion("lavaan")),
      estimator = "MLR"
    )
  )
}

diary_prepare_lagged_mediation <- function(data, spec) {
  if (!identical(spec$temporalEffect, "lagged")) {
    return(list(data = data, spec = spec, laggedPredictorId = NULL))
  }
  subject <- spec$subjectVariableId
  time <- spec$timeVariableId
  predictor <- spec$predictorVariableId
  lag_order <- as.integer(spec$lagOrder)
  lagged_id <- paste0(predictor, "__lag", lag_order)
  gap <- ave(data[[time]], data[[subject]], FUN = function(values) {
    values - c(rep(NA_real_, lag_order), head(values, -lag_order))
  })
  data[[lagged_id]] <- ave(data[[predictor]], data[[subject]], FUN = function(values) {
    c(rep(NA_real_, lag_order), head(values, -lag_order))
  })
  if (!is.null(spec$expectedTimeInterval)) {
    expected_gap <- spec$expectedTimeInterval * lag_order
    tolerance <- if (is.null(spec$timeIntervalTolerance)) 0 else spec$timeIntervalTolerance
    data[[lagged_id]][abs(gap - expected_gap) > tolerance] <- NA_real_
  }
  data <- data[is.finite(data[[lagged_id]]), , drop = FALSE]
  lagged_spec <- spec
  lagged_spec$predictorVariableId <- lagged_id
  list(data = data, spec = lagged_spec, laggedPredictorId = lagged_id)
}

fit_diary_multilevel <- function(data, spec, label_for, confidence_level = 0.95) {
  original_n <- nrow(data)
  quality <- diary_quality_evidence(data, spec)
  quality_filtered <- diary_apply_quality_rules(data, spec, quality)
  reliability <- diary_multilevel_reliability(quality_filtered, spec)
  prepared <- if (identical(spec$missingStrategy, "multilevel_mi")) {
    NULL
  } else {
    validate_diary_data(quality_filtered, spec)
  }
  result <- if (
    identical(spec$analysisType, "lmm") &&
    identical(spec$missingStrategy, "multilevel_mi")
  ) {
    fit_diary_lmm_mi(quality_filtered, spec, label_for, confidence_level)
  } else if (identical(spec$analysisType, "bayesian_dsem")) {
    fit_diary_bayesian_dsem(prepared, spec, label_for, confidence_level)
  } else if (identical(spec$analysisType, "glmm")) {
    fit_diary_glmm(prepared, spec, label_for, confidence_level)
  } else if (identical(spec$analysisType, "mediation")) {
    lagged <- diary_prepare_lagged_mediation(prepared, spec)
    fitted <- fit_diary_mediation(lagged$data, lagged$spec, label_for, confidence_level)
    fitted$temporalEffect <- spec$temporalEffect
    fitted$lagOrder <- spec$lagOrder
    fitted$laggedPredictorId <- lagged$laggedPredictorId
    fitted
  } else if (identical(spec$residualStructure, "ar1")) {
    fit_diary_ar1(prepared, spec, label_for, confidence_level)
  } else {
    fit_diary_lmm(prepared, spec, label_for, confidence_level)
  }
  result$sampleFlow <- list(
    original = original_n,
    afterQualityRules = nrow(quality_filtered),
    included = result$sampleSize,
    excluded = original_n - result$sampleSize,
    missingMethod = "model complete cases after preregistered quality rules"
  )
  result$dataQuality <- quality$evidence
  result$multilevelReliability <- reliability
  if (isTRUE(spec$runRobustnessChecks)) {
    result$robustnessChecks <- list(ensure_result_scenario("主模型", result))
    variants <- list()
    if (spec$analysisType %in% c("lmm", "glmm")) {
      random_spec <- spec
      random_spec$randomSlope <- !isTRUE(spec$randomSlope)
      variants[["切换随机斜率结构"]] <- random_spec
      if (identical(spec$analysisType, "lmm")) {
        residual_spec <- spec
        residual_spec$residualStructure <- if (identical(spec$residualStructure, "ar1")) {
          "independent"
        } else {
          "ar1"
        }
        variants[["切换残差相关结构"]] <- residual_spec
      }
    } else if (
      identical(spec$temporalEffect, "contemporaneous") &&
      !is.null(spec$expectedTimeInterval)
    ) {
      temporal_spec <- spec
      temporal_spec$temporalEffect <- "lagged"
      variants[["滞后中介敏感性"]] <- temporal_spec
    }
    for (scenario in names(variants)) {
      variant <- variants[[scenario]]
      variant$runRobustnessChecks <- FALSE
      variant$powerAnalysis <- NULL
      variant_result <- tryCatch(
        fit_diary_multilevel(data, variant, label_for, confidence_level),
        error = function(error) NULL
      )
      if (!is.null(variant_result)) {
        result$robustnessChecks[[length(result$robustnessChecks) + 1L]] <-
          ensure_result_scenario(scenario, variant_result)
      }
    }
  }
  if (!is.null(spec$powerAnalysis)) {
    result$powerAnalysis <- diary_power_analysis(spec)
  }
  result
}
