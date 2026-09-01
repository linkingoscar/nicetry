.this_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
if (is.null(.this_dir) || nchar(.this_dir) == 0) .this_dir <- "."
if (file.exists(file.path(.this_dir, "diary_utils.R"))) {
  source(file.path(.this_dir, "diary_utils.R"))
  source(file.path(.this_dir, "centering_utils.R"))
  source(file.path(.this_dir, "time_series_utils.R"))
}
panel_finite <- function(value) {
  numeric <- suppressWarnings(as.numeric(value))
  if (length(numeric) == 0L || !is.finite(numeric[[1]])) return(NULL)
  unname(numeric[[1]])
}

panel_fit_indices <- function(fit) {
  values <- tryCatch(
    lavaan::fitMeasures(
      fit,
      c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr", "aic", "bic")
    ),
    error = function(error) NULL
  )
  if (is.null(values)) {
    return(list(
      chiSquare = NULL,
      degreesOfFreedom = NULL,
      pValue = NULL,
      cfi = NULL,
      tli = NULL,
      rmsea = NULL,
      srmr = NULL,
      aic = NULL,
      bic = NULL
    ))
  }
  list(
    chiSquare = ensure_finite(values[["chisq"]]),
    degreesOfFreedom = as.integer(values[["df"]]),
    pValue = ensure_finite(values[["pvalue"]]),
    cfi = ensure_finite(values[["cfi"]]),
    tli = ensure_finite(values[["tli"]]),
    rmsea = ensure_finite(values[["rmsea"]]),
    srmr = ensure_finite(values[["srmr"]]),
    aic = ensure_finite(values[["aic"]]),
    bic = ensure_finite(values[["bic"]])
  )
}

panel_result_scenario <- function(scenario, result) {
  list(
    scenario = scenario,
    modelType = result$modelType,
    estimator = result$estimator,
    missingMethod = result$missingMethod,
    constrainedAcrossTime = result$constrainedAcrossTime,
    sampleSize = result$sampleSize,
    validForInterpretation = result$validForInterpretation,
    fitIndices = result$fitIndices,
    crossLaggedPaths = Filter(
      function(path) identical(path$pathType, "cross_lagged"),
      result$paths
    )
  )
}

panel_path_rows <- function(fit, x_columns, y_columns, confidence_level) {
  parameters <- lavaan::parameterEstimates(
    fit,
    standardized = TRUE,
    ci = TRUE,
    level = confidence_level
  )
  paths <- parameters[parameters$op == "~", , drop = FALSE]
  x_names <- setNames(seq_along(x_columns), x_columns)
  y_names <- setNames(seq_along(y_columns), y_columns)
  within_x <- setNames(seq_along(x_columns), paste0("wx_", seq_along(x_columns)))
  within_y <- setNames(seq_along(y_columns), paste0("wy_", seq_along(y_columns)))
  wave_for <- c(x_names, y_names, within_x, within_y)
  construct_for <- c(
    setNames(rep("X", length(x_columns)), x_columns),
    setNames(rep("Y", length(y_columns)), y_columns),
    setNames(rep("X", length(x_columns)), names(within_x)),
    setNames(rep("Y", length(y_columns)), names(within_y))
  )
  lapply(seq_len(nrow(paths)), function(index) {
    lhs <- as.character(paths$lhs[[index]])
    rhs <- as.character(paths$rhs[[index]])
    lhs_construct <- unname(construct_for[[lhs]])
    rhs_construct <- unname(construct_for[[rhs]])
    list(
      id = paste0(lhs, "~", rhs),
      outcome = lhs,
      predictor = rhs,
      fromWave = as.integer(wave_for[[rhs]]),
      toWave = as.integer(wave_for[[lhs]]),
      pathType = if (identical(lhs_construct, rhs_construct)) "autoregressive" else "cross_lagged",
      direction = paste0(rhs_construct, "→", lhs_construct),
      estimate = ensure_finite(paths$est[[index]]),
      standardizedEstimate = ensure_finite(paths$std.all[[index]]),
      standardError = ensure_finite(paths$se[[index]]),
      statistic = ensure_finite(paths$z[[index]]),
      pValue = ensure_finite(paths$pvalue[[index]]),
      lower = ensure_finite(paths$ci.lower[[index]]),
      upper = ensure_finite(paths$ci.upper[[index]])
    )
  })
}

fit_longitudinal_panel <- function(data, spec, label_for, confidence_level = 0.95) {
  suppressPackageStartupMessages(library(lavaan))
  if (identical(spec$measurementMode, "latent_items")) {
    return(fit_latent_longitudinal_panel(
      data,
      spec,
      label_for,
      confidence_level
    ))
  }
  waves <- spec$waves
  model_type <- spec$modelType
  x_columns <- vapply(waves, function(wave) wave$xVariableId, character(1))
  y_columns <- vapply(waves, function(wave) wave$yVariableId, character(1))
  subject_id <- spec$subjectVariableId
  required <- unique(c(subject_id, x_columns, y_columns))
  missing_columns <- setdiff(required, names(data))
  if (length(missing_columns) > 0L) {
    stop(paste0("LONGITUDINAL_COLUMNS_NOT_FOUND: ", paste(missing_columns, collapse = ", ")))
  }
  if (anyDuplicated(data[[subject_id]][!is.na(data[[subject_id]])])) {
    stop("LONGITUDINAL_SUBJECT_ID_NOT_UNIQUE_FOR_WIDE_DATA")
  }
  numeric_data <- data[, c(x_columns, y_columns), drop = FALSE]
  for (column in names(numeric_data)) {
    numeric_data[[column]] <- suppressWarnings(as.numeric(numeric_data[[column]]))
  }
  if (any(vapply(numeric_data, function(column) {
    finite <- column[is.finite(column)]
    length(finite) < 3L || length(unique(finite)) < 2L
  }, logical(1)))) {
    stop("LONGITUDINAL_VARIABLE_HAS_INSUFFICIENT_VARIATION")
  }

  constrained <- isTRUE(spec$constrainAcrossTime)
  label <- function(prefix, index) if (constrained) prefix else paste0(prefix, index)
  syntax <- character(0)
  if (identical(model_type, "clpm")) {
    syntax <- c(syntax, paste0(x_columns[[1]], " ~~ ", y_columns[[1]]))
    for (index in 2:length(waves)) {
      previous <- index - 1L
      syntax <- c(
        syntax,
        sprintf(
          "%s ~ %s*%s + %s*%s",
          x_columns[[index]], label("ar_x", previous), x_columns[[previous]],
          label("cl_yx", previous), y_columns[[previous]]
        ),
        sprintf(
          "%s ~ %s*%s + %s*%s",
          y_columns[[index]], label("ar_y", previous), y_columns[[previous]],
          label("cl_xy", previous), x_columns[[previous]]
        ),
        paste0(x_columns[[index]], " ~~ ", y_columns[[index]])
      )
    }
  } else if (identical(model_type, "ri_clpm")) {
    syntax <- c(
      paste0("RI_X =~ ", paste(paste0("1*", x_columns), collapse = " + ")),
      paste0("RI_Y =~ ", paste(paste0("1*", y_columns), collapse = " + ")),
      "RI_X ~~ RI_Y"
    )
    for (index in seq_along(waves)) {
      wx <- paste0("wx_", index)
      wy <- paste0("wy_", index)
      syntax <- c(
        syntax,
        paste0(wx, " =~ 1*", x_columns[[index]]),
        paste0(wy, " =~ 1*", y_columns[[index]]),
        paste0(x_columns[[index]], " ~~ 0*", x_columns[[index]]),
        paste0(y_columns[[index]], " ~~ 0*", y_columns[[index]]),
        paste0(wx, " ~~ ", wy),
        paste0("RI_X ~~ 0*", wx),
        paste0("RI_X ~~ 0*", wy),
        paste0("RI_Y ~~ 0*", wx),
        paste0("RI_Y ~~ 0*", wy)
      )
      if (index > 1L) {
        previous <- index - 1L
        syntax <- c(
          syntax,
          sprintf(
            "%s ~ %s*wx_%s + %s*wy_%s",
            wx, label("ar_x", previous), previous,
            label("cl_yx", previous), previous
          ),
          sprintf(
            "%s ~ %s*wy_%s + %s*wx_%s",
            wy, label("ar_y", previous), previous,
            label("cl_xy", previous), previous
          )
        )
      }
    }
  } else {
    stop("LONGITUDINAL_MODEL_TYPE_NOT_SUPPORTED")
  }

  captured_warnings <- character(0)
  fit <- withCallingHandlers(
    lavaan::sem(
      paste(syntax, collapse = "\n"),
      data = numeric_data,
      estimator = spec$estimator,
      missing = if (identical(spec$missing, "fiml")) "fiml" else "listwise",
      auto.fix.first = FALSE,
      auto.var = TRUE
    ),
    warning = function(warning) {
      captured_warnings <<- c(captured_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )
  if (!isTRUE(lavaan::lavInspect(fit, "converged"))) stop("LONGITUDINAL_NONCONVERGENCE")

  parameter_table <- lavaan::parameterEstimates(fit)
  negative_variances <- parameter_table[
    parameter_table$op == "~~" &
      parameter_table$lhs == parameter_table$rhs &
      parameter_table$est < -1e-8,
    ,
    drop = FALSE
  ]
  post_check <- isTRUE(lavaan::lavInspect(fit, "post.check"))
  diagnostic_rows <- lapply(unique(captured_warnings), function(message) {
    list(code = "LAVAAN_WARNING", severity = "warning", message = message)
  })
  if (nrow(negative_variances) > 0L) {
    diagnostic_rows[[length(diagnostic_rows) + 1L]] <- list(
      code = "NEGATIVE_VARIANCE",
      severity = "warning",
      message = paste0(
        "模型出现负方差估计：",
        paste(unique(negative_variances$lhs), collapse = "、"),
        "。相关路径仅用于诊断。"
      )
    )
  }
  if (!post_check) {
    diagnostic_rows[[length(diagnostic_rows) + 1L]] <- list(
      code = "POST_ESTIMATION_INVALID",
      severity = "warning",
      message = "lavaan 后估计检查未通过；请检查方差边界和协方差矩阵。"
    )
  }
  if (identical(model_type, "clpm") && length(waves) == 2L) {
    diagnostic_rows[[length(diagnostic_rows) + 1L]] <- list(
      code = "TWO_WAVE_CLPM_LIMITATION",
      severity = "warning",
      message = "两时点 CLPM 不能分离稳定个体差异，整体拟合指标也可能缺少诊断信息。"
    )
  }

  wave_flow <- lapply(seq_along(waves), function(index) {
    observed <- complete.cases(numeric_data[, c(x_columns[[index]], y_columns[[index]]), drop = FALSE])
    previous <- if (index == 1L) rep(TRUE, nrow(numeric_data)) else complete.cases(
      numeric_data[, c(x_columns[[index - 1L]], y_columns[[index - 1L]]), drop = FALSE]
    )
    list(
      label = waves[[index]]$label,
      timeValue = waves[[index]]$timeValue,
      observed = sum(observed),
      retainedFromPrevious = sum(previous & observed),
      attritionFromPrevious = if (index == 1L) 0L else sum(previous & !observed),
      reenteredFromPrevious = if (index == 1L) 0L else sum(!previous & observed)
    )
  })

  result <- list(
    available = TRUE,
    modelType = model_type,
    modelLabel = if (identical(model_type, "ri_clpm")) "RI-CLPM" else "CLPM",
    measurementMode = "observed_scores",
    subjectVariableId = subject_id,
    subjectLabel = label_for(subject_id),
    constructLabels = list(
      x = label_for(x_columns[[1]]),
      y = label_for(y_columns[[1]])
    ),
    waveCount = length(waves),
    sampleSize = as.integer(lavaan::lavInspect(fit, "ntotal")),
    estimator = spec$estimator,
    missingMethod = spec$missing,
    constrainedAcrossTime = constrained,
    fitIndices = panel_fit_indices(fit),
    paths = panel_path_rows(fit, x_columns, y_columns, confidence_level),
    waveSampleFlow = wave_flow,
    diagnostics = diagnostic_rows,
    validForInterpretation = post_check && nrow(negative_variances) == 0L,
    causalNotice = "交叉滞后路径提供时间先后与方向性关联证据；没有随机化或充分识别假设时不能自动解释为因果效应。",
    provenance = list(
      engine = "R lavaan",
      engineVersion = as.character(packageVersion("lavaan")),
      estimand = if (identical(model_type, "ri_clpm")) {
        "within-person autoregressive and cross-lagged association"
      } else {
        "observed-score autoregressive and cross-lagged association"
      }
    )
  )
  if (isTRUE(spec$compareCompetingModels) && length(waves) >= 3L) {
    alternative_spec <- spec
    alternative_spec$modelType <- if (identical(model_type, "ri_clpm")) "clpm" else "ri_clpm"
    alternative_spec$compareCompetingModels <- FALSE
    alternative_spec$runRobustnessChecks <- FALSE
    alternative_spec$powerAnalysis <- NULL
    alternative <- tryCatch(
      fit_longitudinal_panel(data, alternative_spec, label_for, confidence_level),
      error = function(error) NULL
    )
    result$competingModels <- c(
      list(list(
        modelType = result$modelType,
        modelLabel = result$modelLabel,
        converged = TRUE,
        fitIndices = result$fitIndices
      )),
      if (is.null(alternative)) list() else list(list(
        modelType = alternative$modelType,
        modelLabel = alternative$modelLabel,
        converged = TRUE,
        fitIndices = alternative$fitIndices
      ))
    )
  }
  if (isTRUE(spec$runRobustnessChecks)) {
    result$robustnessChecks <- list(panel_result_scenario("主模型", result))
    constraint_spec <- spec
    constraint_spec$constrainAcrossTime <- !isTRUE(spec$constrainAcrossTime)
    constraint_spec$compareCompetingModels <- FALSE
    constraint_spec$runRobustnessChecks <- FALSE
    constraint_spec$powerAnalysis <- NULL
    constraint_result <- tryCatch(
      fit_longitudinal_panel(data, constraint_spec, label_for, confidence_level),
      error = function(error) NULL
    )
    if (!is.null(constraint_result)) {
      result$robustnessChecks[[length(result$robustnessChecks) + 1L]] <-
        panel_result_scenario("切换跨时路径等值约束", constraint_result)
    }
    if (anyNA(numeric_data)) {
      missing_spec <- spec
      missing_spec$missing <- if (identical(spec$missing, "fiml")) {
        "complete_cases"
      } else {
        "fiml"
      }
      missing_spec$compareCompetingModels <- FALSE
      missing_spec$runRobustnessChecks <- FALSE
      missing_spec$powerAnalysis <- NULL
      missing_result <- tryCatch(
        fit_longitudinal_panel(data, missing_spec, label_for, confidence_level),
        error = function(error) NULL
      )
      if (!is.null(missing_result)) {
        result$robustnessChecks[[length(result$robustnessChecks) + 1L]] <-
          panel_result_scenario("切换缺失数据策略", missing_result)
      }
    }
  }
  if (!is.null(spec$powerAnalysis)) {
    result$powerAnalysis <- longitudinal_power_analysis(spec)
  }
  result
}
