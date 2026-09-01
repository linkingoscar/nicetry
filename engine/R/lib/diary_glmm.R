# 独立加载（测试/复用）时引导 seed 工具；入口脚本已先行 source。
if (!exists("researchpath_seed", mode = "function", inherits = TRUE)) {
  if (file.exists(file.path("engine", "R", "lib", "seed_utils.R"))) {
    source(file.path("engine", "R", "lib", "seed_utils.R"))
  }
}

.this_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
if (is.null(.this_dir) || nchar(.this_dir) == 0) .this_dir <- "."
if (file.exists(file.path(.this_dir, "diary_utils.R"))) {
  source(file.path(.this_dir, "diary_utils.R"))
  source(file.path(.this_dir, "centering_utils.R"))
  source(file.path(.this_dir, "time_series_utils.R"))
}
diary_glmm_validate_outcome <- function(data, spec) {
  outcome <- data[[spec$outcomeVariableId]]
  if (identical(spec$outcomeFamily, "binomial")) {
    if (!all(outcome %in% c(0, 1))) stop("GLMM_BINOMIAL_OUTCOME_MUST_BE_ZERO_ONE")
  } else {
    if (any(outcome < 0) || any(abs(outcome - round(outcome)) > 1e-8)) {
      stop("GLMM_COUNT_OUTCOME_MUST_BE_NONNEGATIVE_INTEGER")
    }
  }
  if (!is.null(spec$exposureVariableId)) {
    exposure <- data[[spec$exposureVariableId]]
    if (any(!is.finite(exposure) | exposure <= 0)) {
      stop("GLMM_EXPOSURE_MUST_BE_FINITE_POSITIVE")
    }
  }
}

diary_glmm_coefficient_rows <- function(coefficients, confidence_level, label_for) {
  if (is.null(coefficients) || nrow(coefficients) == 0L) return(list())
  coefficients <- as.data.frame(coefficients)
  coefficients$term <- rownames(coefficients)
  rownames(coefficients) <- NULL
  critical <- qnorm(1 - (1 - confidence_level) / 2)
  lapply(seq_len(nrow(coefficients)), function(index) {
    estimate <- coefficients$Estimate[[index]]
    standard_error <- coefficients$`Std. Error`[[index]]
    lower <- estimate - critical * standard_error
    upper <- estimate + critical * standard_error
    statistic_column <- intersect(c("z value", "t value"), names(coefficients))[[1]]
    probability_column <- grep("^Pr\\(", names(coefficients), value = TRUE)[[1]]
    list(
      term = coefficients$term[[index]],
      label = label_for(coefficients$term[[index]]),
      estimate = ensure_finite(estimate),
      standardError = ensure_finite(standard_error),
      degreesOfFreedom = NULL,
      statistic = ensure_finite(coefficients[[statistic_column]][[index]]),
      pValue = ensure_finite(coefficients[[probability_column]][[index]]),
      lower = ensure_finite(lower),
      upper = ensure_finite(upper),
      exponentiatedEstimate = ensure_finite(exp(estimate)),
      exponentiatedLower = ensure_finite(exp(lower)),
      exponentiatedUpper = ensure_finite(exp(upper))
    )
  })
}

diary_glmm_coefficients <- function(fit, confidence_level, label_for, component = "cond") {
  if (inherits(fit, "glmmTMB")) {
    diary_glmm_coefficient_rows(
      coef(summary(fit))[[component]],
      confidence_level,
      label_for
    )
  } else {
    diary_glmm_coefficient_rows(coef(summary(fit)), confidence_level, label_for)
  }
}

diary_glmm_simulation_diagnostics <- function(fit, data, spec) {
  outcome <- data[[spec$outcomeVariableId]]
  pearson <- suppressWarnings(residuals(fit, type = "pearson"))
  residual_df <- df.residual(fit)
  pearson_dispersion <- if (residual_df > 0) {
    sum(pearson^2, na.rm = TRUE) / residual_df
  } else {
    NA_real_
  }
  if (identical(spec$outcomeFamily, "binomial")) {
    return(list(
      pearsonDispersion = ensure_finite(pearson_dispersion),
      observedZeroRate = NULL,
      expectedZeroRate = NULL,
      zeroRateDifference = NULL,
      simulationCount = 0L,
      dispersionRatio = NULL,
      dispersionPValue = NULL,
      zeroInflationPValue = NULL,
      diagnosticMethod = "Pearson residual dispersion"
    ))
  }
  simulation_count <- as.integer(spec$distributionDiagnosticSimulations)
  set.seed(researchpath_seed(spec$distributionDiagnosticSeed))
  simulations <- as.matrix(simulate(fit, nsim = simulation_count))
  simulated_mean <- rowMeans(simulations)
  simulated_variance <- apply(simulations, 1L, var)
  simulated_variance[!is.finite(simulated_variance) | simulated_variance < 1e-8] <- 1e-8
  standardized_discrepancy <- function(values) {
    mean((values - simulated_mean)^2 / simulated_variance)
  }
  observed_discrepancy <- standardized_discrepancy(outcome)
  simulated_discrepancies <- apply(simulations, 2L, standardized_discrepancy)
  dispersion_reference <- median(simulated_discrepancies)
  dispersion_p <- (
    1 + sum(simulated_discrepancies >= observed_discrepancy)
  ) / (simulation_count + 1)
  observed_zero <- mean(outcome == 0)
  simulated_zero <- colMeans(simulations == 0)
  zero_p <- (1 + sum(simulated_zero >= observed_zero)) / (simulation_count + 1)
  expected_zero <- mean(simulated_zero)
  list(
    pearsonDispersion = ensure_finite(pearson_dispersion),
    observedZeroRate = ensure_finite(observed_zero),
    expectedZeroRate = ensure_finite(expected_zero),
    zeroRateDifference = ensure_finite(observed_zero - expected_zero),
    simulationCount = simulation_count,
    dispersionRatio = ensure_finite(observed_discrepancy / dispersion_reference),
    dispersionPValue = ensure_finite(dispersion_p),
    zeroInflationPValue = ensure_finite(zero_p),
    diagnosticMethod = paste0(
      "Parametric simulation under the fitted conditional model (",
      simulation_count,
      " replicates; one-sided excess-dispersion and excess-zero checks)"
    )
  )
}

diary_glmm_random_terms <- function(spec, random_predictor) {
  subject_inside <- if (isTRUE(spec$randomSlope)) {
    paste0("1 + ", random_predictor)
  } else {
    "1"
  }
  terms <- paste0("(", subject_inside, " | ", spec$subjectVariableId, ")")
  if (identical(spec$clusterStructure, "cross_classified")) {
    terms <- c(terms, paste0("(1 | ", spec$crossClassVariableId, ")"))
  }
  terms
}

diary_count_family <- function(spec, baseline = FALSE) {
  count_model <- if (baseline) "standard" else spec$countModel
  if (identical(spec$outcomeFamily, "poisson")) {
    if (identical(count_model, "hurdle")) {
      glmmTMB::truncated_poisson(link = "log")
    } else {
      poisson(link = "log")
    }
  } else if (identical(count_model, "hurdle")) {
    glmmTMB::truncated_nbinom2(link = "log")
  } else {
    glmmTMB::nbinom2(link = "log")
  }
}

diary_count_zero_formula <- function(spec, fixed, baseline = FALSE) {
  if (baseline || identical(spec$countModel, "standard")) return(~0)
  if (identical(spec$zeroProcessPredictors, "shared") && length(fixed) > 0L) {
    as.formula(paste("~", paste(fixed, collapse = " + ")))
  } else {
    ~1
  }
}

diary_fit_count_model <- function(formula, data, spec, fixed, baseline = FALSE) {
  glmmTMB::glmmTMB(
    formula,
    ziformula = diary_count_zero_formula(spec, fixed, baseline),
    data = data,
    family = diary_count_family(spec, baseline),
    control = glmmTMB::glmmTMBControl(
      optimizer = stats::nlminb,
      optCtrl = list(iter.max = 10000, eval.max = 15000)
    )
  )
}

diary_glmm_fit_status <- function(fit) {
  if (inherits(fit, "glmmTMB")) {
    convergence <- identical(fit$fit$convergence, 0L)
    positive_hessian <- isTRUE(fit$sdr$pdHess)
    list(
      converged = convergence && positive_hessian,
      positiveDefiniteHessian = positive_hessian,
      messages = unique(c(
        if (!convergence) fit$fit$message else character(0),
        if (!positive_hessian) "Hessian is not positive definite." else character(0)
      ))
    )
  } else {
    messages <- unlist(fit@optinfo$conv$lme4$messages)
    list(
      converged = length(messages) == 0L,
      positiveDefiniteHessian = TRUE,
      messages = messages
    )
  }
}

diary_glmm_variance_components <- function(fit) {
  if (inherits(fit, "glmmTMB")) {
    groups <- glmmTMB::VarCorr(fit)$cond
    rows <- list()
    for (group in names(groups)) {
      covariance <- as.matrix(groups[[group]])
      deviations <- attr(groups[[group]], "stddev")
      correlations <- attr(groups[[group]], "correlation")
      terms <- colnames(covariance)
      for (index in seq_along(terms)) {
        rows[[length(rows) + 1L]] <- list(
          group = group,
          term = terms[[index]],
          pairedTerm = NULL,
          variance = ensure_finite(covariance[index, index]),
          standardDeviation = ensure_finite(deviations[[index]])
        )
      }
      if (length(terms) > 1L) {
        for (first in seq_len(length(terms) - 1L)) {
          for (second in (first + 1L):length(terms)) {
            rows[[length(rows) + 1L]] <- list(
              group = group,
              term = terms[[first]],
              pairedTerm = terms[[second]],
              variance = ensure_finite(covariance[first, second]),
              standardDeviation = ensure_finite(correlations[first, second])
            )
          }
        }
      }
    }
    return(rows)
  }
  variance <- as.data.frame(lme4::VarCorr(fit))
  lapply(seq_len(nrow(variance)), function(index) {
    list(
      group = as.character(variance$grp[[index]]),
      term = as.character(variance$var1[[index]]),
      pairedTerm = if (is.na(variance$var2[[index]])) {
        NULL
      } else {
        as.character(variance$var2[[index]])
      },
      variance = ensure_finite(variance$vcov[[index]]),
      standardDeviation = ensure_finite(variance$sdcor[[index]])
    )
  })
}

diary_glmm_model_comparison_row <- function(fit, model, label) {
  likelihood <- logLik(fit)
  status <- diary_glmm_fit_status(fit)
  list(
    model = model,
    label = label,
    aic = ensure_finite(AIC(fit)),
    bic = ensure_finite(BIC(fit)),
    logLikelihood = ensure_finite(as.numeric(likelihood)),
    parameterCount = ensure_finite(attr(likelihood, "df")),
    converged = status$converged
  )
}

diary_glmm_model_label <- function(spec) {
  family_label <- if (identical(spec$outcomeFamily, "poisson")) "Poisson" else "负二项"
  core <- if (identical(spec$outcomeFamily, "binomial")) {
    "二元 Logit GLMM"
  } else {
    switch(
      spec$countModel,
      standard = paste(family_label, "计数 GLMM"),
      zero_inflated = paste("零膨胀", family_label, "GLMM"),
      hurdle = paste("Hurdle", family_label, "GLMM")
    )
  }
  paste0(
    core,
    if (identical(spec$clusterStructure, "cross_classified")) "（交叉分类）" else ""
  )
}

fit_diary_glmm <- function(data, spec, label_for, confidence_level) {
  if (is.null(spec$countModel)) spec$countModel <- "standard"
  if (is.null(spec$zeroProcessPredictors)) spec$zeroProcessPredictors <- "intercept_only"
  if (is.null(spec$distributionDiagnosticSimulations)) {
    spec$distributionDiagnosticSimulations <- 250L
  }
  if (is.null(spec$distributionDiagnosticSeed)) {
    spec$distributionDiagnosticSeed <- 20260729L
  }
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
  complete_ids <- unique(c(
    spec$outcomeVariableId,
    spec$subjectVariableId,
    spec$crossClassVariableId,
    spec$exposureVariableId,
    fixed
  ))
  complete_ids <- complete_ids[!is.na(complete_ids) & nzchar(complete_ids)]
  data <- data[complete.cases(data[, complete_ids, drop = FALSE]), , drop = FALSE]
  if (nrow(data) < 20L) stop("GLMM_INSUFFICIENT_COMPLETE_OBSERVATIONS")
  diary_glmm_validate_outcome(data, spec)
  random_predictor <- if (
    identical(spec$temporalEffect, "lagged") && !is.null(temporal$laggedPredictorId)
  ) {
    temporal$laggedPredictorId
  } else {
    centered$within
  }
  offset_term <- if (is.null(spec$exposureVariableId)) {
    character(0)
  } else {
    paste0("offset(log(", spec$exposureVariableId, "))")
  }
  formula <- as.formula(paste(
    spec$outcomeVariableId,
    "~",
    paste(c(
      fixed,
      offset_term,
      diary_glmm_random_terms(spec, random_predictor)
    ), collapse = " + ")
  ))
  captured_warnings <- character(0)
  fit <- withCallingHandlers(
    if (identical(spec$outcomeFamily, "binomial")) {
      suppressPackageStartupMessages(library(lme4))
      lme4::glmer(
        formula,
        data = data,
        family = binomial(link = "logit"),
        nAGQ = 1L,
        control = lme4::glmerControl(optimizer = "bobyqa")
      )
    } else {
      if (!suppressWarnings(requireNamespace("glmmTMB", quietly = TRUE))) {
        stop("GLMMTMB_PACKAGE_REQUIRED_FOR_COUNT_MODELS")
      }
      diary_fit_count_model(formula, data, spec, fixed)
    },
    warning = function(warning) {
      captured_warnings <<- c(captured_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )
  status <- diary_glmm_fit_status(fit)
  variance_components <- format_variance_components(fit)
  singular <- any(vapply(variance_components, function(component) {
    is.null(component$pairedTerm) &&
      !is.null(component$standardDeviation) &&
      component$standardDeviation < 1e-4
  }, logical(1)))
  distribution <- diary_glmm_simulation_diagnostics(fit, data, spec)
  diagnostics <- lapply(unique(c(captured_warnings, status$messages)), function(message) {
    list(code = "GLMM_WARNING", severity = "warning", message = message)
  })
  if (singular) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "GLMM_SINGULAR_FIT",
      severity = "warning",
      message = "GLMM 至少一个随机效应标准差接近零，随机结构位于奇异边界。"
    )
  }
  if (
    !is.null(distribution$dispersionPValue) &&
    distribution$dispersionPValue < 0.05
  ) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "GLMM_OVERDISPERSION",
      severity = "warning",
      message = paste0(
        "参数模拟显示剩余过度离散（单侧 p=",
        format(round(distribution$dispersionPValue, 4), nsmall = 4),
        "）；应复核结局族、随机结构和遗漏异质性。"
      )
    )
  }
  if (
    !is.null(distribution$zeroInflationPValue) &&
    distribution$zeroInflationPValue < 0.05
  ) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "GLMM_EXCESS_ZEROS",
      severity = "warning",
      message = if (identical(spec$countModel, "standard")) {
        paste0(
          "参数模拟显示观测零值显著多于当前模型预期（单侧 p=",
          format(round(distribution$zeroInflationPValue, 4), nsmall = 4),
          "）。平台不会自动换模；请根据结构零或两阶段过程的理论选择零膨胀/Hurdle。"
        )
      } else {
        "所选零值模型仍未充分复现观测零比例；结果不宜直接解释。"
      }
    )
  }
  fixed_effects <- diary_glmm_coefficients(fit, confidence_level, label_for)
  zero_effects <- if (
    inherits(fit, "glmmTMB") && !identical(spec$countModel, "standard")
  ) {
    diary_glmm_coefficients(fit, confidence_level, label_for, "zi")
  } else {
    list()
  }
  if (
    identical(spec$outcomeFamily, "binomial") &&
    any(vapply(fixed_effects, function(row) abs(row$estimate) > 10, logical(1)))
  ) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "GLMM_POSSIBLE_SEPARATION",
      severity = "warning",
      message = "Logit 系数绝对值超过 10，可能存在完全或近完全分离。"
    )
  }
  comparison <- list()
  if (!identical(spec$outcomeFamily, "binomial")) {
    comparison[[1L]] <- diary_glmm_model_comparison_row(
      fit,
      spec$countModel,
      diary_glmm_model_label(spec)
    )
    if (!identical(spec$countModel, "standard")) {
      baseline <- tryCatch(
        diary_fit_count_model(formula, data, spec, fixed, baseline = TRUE),
        error = function(error) NULL
      )
      if (!is.null(baseline)) {
        comparison[[2L]] <- diary_glmm_model_comparison_row(
          baseline,
          "standard",
          paste0(
            if (identical(spec$outcomeFamily, "poisson")) "Poisson" else "负二项",
            "计数 GLMM（基准）"
          )
        )
      }
    }
  }
  method_notice <- if (identical(spec$countModel, "zero_inflated")) {
    "零膨胀模型把零值分为结构零与计数过程产生的抽样零；零过程与条件计数过程必须分别解释。"
  } else if (identical(spec$countModel, "hurdle")) {
    "Hurdle 模型分别估计是否跨过零门槛及跨过门槛后的正计数；条件 IRR 仅适用于正计数过程。"
  } else if (!identical(spec$outcomeFamily, "binomial")) {
    "标准计数 GLMM 不假设额外结构零过程；零值模型只在理论与模拟诊断共同支持时显式启用。"
  } else {
    NULL
  }
  list(
    available = TRUE,
    analysisType = "glmm",
    modelLabel = diary_glmm_model_label(spec),
    sampleSize = nrow(data),
    personCount = length(unique(data[[spec$subjectVariableId]])),
    crossClassCount = if (identical(spec$clusterStructure, "cross_classified")) {
      length(unique(data[[spec$crossClassVariableId]]))
    } else {
      NULL
    },
    observationsPerPerson = list(
      minimum = min(table(data[[spec$subjectVariableId]])),
      median = unname(median(table(data[[spec$subjectVariableId]]))),
      maximum = max(table(data[[spec$subjectVariableId]]))
    ),
    formula = paste(deparse(formula), collapse = " "),
    outcomeFamily = spec$outcomeFamily,
    countModel = spec$countModel,
    zeroProcessPredictors = spec$zeroProcessPredictors,
    linkFunction = if (identical(spec$outcomeFamily, "binomial")) "logit" else "log",
    effectScale = if (identical(spec$outcomeFamily, "binomial")) {
      "odds ratio"
    } else {
      "incidence rate ratio"
    },
    clusterStructure = spec$clusterStructure,
    crossClassVariableId = spec$crossClassVariableId,
    exposureVariableId = spec$exposureVariableId,
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
    fixedEffects = fixed_effects,
    zeroProcessEffects = zero_effects,
    varianceComponents = variance_components,
    countModelComparison = comparison,
    distributionDiagnostics = distribution,
    residualStructure = "conditional distribution",
    singular = singular,
    randomSlope = isTRUE(spec$randomSlope),
    diagnostics = diagnostics,
    validForInterpretation = status$converged && !singular && !(
      !is.null(distribution$zeroInflationPValue) &&
        distribution$zeroInflationPValue < 0.05 &&
        !identical(spec$countModel, "standard")
    ),
    methodNotice = method_notice,
    provenance = list(
      engine = if (inherits(fit, "glmmTMB")) "R glmmTMB" else "R lme4",
      engineVersion = if (inherits(fit, "glmmTMB")) {
        as.character(packageVersion("glmmTMB"))
      } else {
        as.character(packageVersion("lme4"))
      },
      estimator = "maximum likelihood with Laplace approximation",
      diagnosticSeed = spec$distributionDiagnosticSeed,
      diagnosticSimulations = spec$distributionDiagnosticSimulations,
      automaticModelSwitching = FALSE
    )
  )
}
