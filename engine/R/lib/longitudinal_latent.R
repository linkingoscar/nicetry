latent_panel_level_index <- function(level) {
  match(level, c("configural", "metric", "scalar", "strict"))
}

latent_panel_item_map <- function(waves) {
  list(
    x = lapply(waves, function(wave) unlist(wave$xItemIds, use.names = FALSE)),
    y = lapply(waves, function(wave) unlist(wave$yItemIds, use.names = FALSE))
  )
}

latent_panel_factor_names <- function(waves) {
  list(
    x = paste0("lx_t", seq_along(waves)),
    y = paste0("ly_t", seq_along(waves))
  )
}

latent_panel_measurement_syntax <- function(
  data,
  waves,
  level,
  indicator_scale,
  partial_positions = character(0)
) {
  items <- latent_panel_item_map(waves)
  factors <- latent_panel_factor_names(waves)
  level_index <- latent_panel_level_index(level)
  syntax <- character(0)
  for (construct in c("x", "y")) {
    for (wave_index in seq_along(waves)) {
      wave_items <- items[[construct]][[wave_index]]
      loadings <- vapply(seq_along(wave_items), function(position) {
        item <- wave_items[[position]]
        partial <- paste0(construct, ":", position) %in% partial_positions
        if (position == 1L) return(paste0("1*", item))
        if (level_index >= 2L && !partial) {
          paste0("l_", construct, "_", position, "*", item)
        } else {
          item
        }
      }, character(1))
      syntax <- c(
        syntax,
        paste0(factors[[construct]][[wave_index]], " =~ ", paste(loadings, collapse = " + "))
      )
      for (position in seq_along(wave_items)) {
        item <- wave_items[[position]]
        partial <- paste0(construct, ":", position) %in% partial_positions
        if (identical(indicator_scale, "continuous") && level_index >= 3L) {
          prefix <- if (partial) {
            paste0("i_", construct, "_", position, "_t", wave_index)
          } else {
            paste0("i_", construct, "_", position)
          }
          syntax <- c(syntax, paste0(item, " ~ ", prefix, "*1"))
        }
        if (level_index >= 4L) {
          prefix <- if (partial) {
            paste0("e_", construct, "_", position, "_t", wave_index)
          } else {
            paste0("e_", construct, "_", position)
          }
          syntax <- c(syntax, paste0(item, " ~~ ", prefix, "*", item))
        }
        if (identical(indicator_scale, "ordinal") && level_index >= 3L) {
          categories <- sort(unique(data[[item]][!is.na(data[[item]])]))
          threshold_count <- length(categories) - 1L
          if (threshold_count < 1L) stop("LATENT_PANEL_ORDINAL_ITEM_HAS_FEWER_THAN_TWO_CATEGORIES")
          labels <- vapply(seq_len(threshold_count), function(threshold) {
            prefix <- if (partial) {
              paste0("th_", construct, "_", position, "_t", wave_index, "_", threshold)
            } else {
              paste0("th_", construct, "_", position, "_", threshold)
            }
            paste0(prefix, "*t", threshold)
          }, character(1))
          syntax <- c(syntax, paste0(item, " | ", paste(labels, collapse = " + ")))
        }
      }
    }
  }

  for (construct in c("x", "y")) {
    position_count <- length(items[[construct]][[1]])
    for (position in seq_len(position_count)) {
      corresponding <- vapply(items[[construct]], function(wave_items) {
        wave_items[[position]]
      }, character(1))
      if (length(corresponding) > 1L) {
        pairs <- combn(corresponding, 2L)
        syntax <- c(
          syntax,
          vapply(seq_len(ncol(pairs)), function(index) {
            paste0(pairs[1L, index], " ~~ ", pairs[2L, index])
          }, character(1))
        )
      }
    }
  }
  for (wave_index in seq_along(waves)) {
    syntax <- c(
      syntax,
      paste0(factors$x[[wave_index]], " ~~ ", factors$y[[wave_index]])
    )
  }
  list(syntax = syntax, items = items, factors = factors)
}

latent_panel_fit <- function(syntax, data, spec, item_ids, ordered = FALSE) {
  captured_warnings <- character(0)
  fit <- withCallingHandlers(
    lavaan::sem(
      paste(unique(syntax), collapse = "\n"),
      data = data,
      estimator = spec$estimator,
      missing = if (identical(spec$missing, "fiml")) "fiml" else "listwise",
      ordered = if (ordered) item_ids else NULL,
      parameterization = if (ordered) "theta" else "delta",
      meanstructure = TRUE,
      auto.var = TRUE
    ),
    warning = function(warning) {
      captured_warnings <<- c(captured_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )
  list(fit = fit, warnings = unique(captured_warnings))
}

latent_panel_invariance_row <- function(level, fit) {
  indices <- panel_fit_indices(fit)
  list(
    level = level,
    label = switch(
      level,
      configural = "配置等值",
      metric = "载荷等值",
      scalar = "截距/阈值等值",
      strict = "严格等值"
    ),
    converged = isTRUE(lavaan::lavInspect(fit, "converged")),
    sampleSize = as.integer(lavaan::lavInspect(fit, "ntotal")),
    fitIndices = indices
  )
}

latent_panel_comparison <- function(previous_level, current_level, previous_fit, current_fit) {
  previous <- panel_fit_indices(previous_fit)
  current <- panel_fit_indices(current_fit)
  lrt <- tryCatch(
    suppressWarnings(lavaan::lavTestLRT(previous_fit, current_fit)),
    error = function(error) NULL
  )
  lrt_row <- if (!is.null(lrt) && nrow(lrt) >= 2L) lrt[nrow(lrt), , drop = FALSE] else NULL
  delta_cfi <- if (is.null(previous$cfi) || is.null(current$cfi)) NULL else current$cfi - previous$cfi
  delta_rmsea <- if (is.null(previous$rmsea) || is.null(current$rmsea)) NULL else current$rmsea - previous$rmsea
  delta_srmr <- if (is.null(previous$srmr) || is.null(current$srmr)) NULL else current$srmr - previous$srmr
  srmr_limit <- if (identical(current_level, "metric")) 0.03 else 0.01
  passes <- !is.null(delta_cfi) && !is.null(delta_rmsea) && !is.null(delta_srmr) &&
    abs(delta_cfi) <= 0.01 && delta_rmsea <= 0.015 && delta_srmr <= srmr_limit
  list(
    from = previous_level,
    to = current_level,
    deltaCfi = panel_finite(delta_cfi),
    deltaRmsea = panel_finite(delta_rmsea),
    deltaSrmr = panel_finite(delta_srmr),
    chiSquareDifference = if (is.null(lrt_row)) NULL else panel_finite(lrt_row[["Chisq diff"]]),
    degreesOfFreedomDifference = if (is.null(lrt_row)) NULL else panel_finite(lrt_row[["Df diff"]]),
    pValue = if (is.null(lrt_row)) NULL else panel_finite(lrt_row[["Pr(>Chisq)"]]),
    passesPracticalCriteria = passes,
    criteria = paste0("|ΔCFI|≤.010, ΔRMSEA≤.015, ΔSRMR≤.", if (srmr_limit == 0.03) "030" else "010")
  )
}

latent_panel_structural_syntax <- function(
  factors,
  model_type,
  constrained,
  waves = NULL,
  growth_shape = "linear"
) {
  wave_count <- length(factors$x)
  label <- function(prefix, index) if (constrained) prefix else paste0(prefix, index)
  syntax <- character(0)
  if (identical(model_type, "clpm")) {
    for (index in 2:wave_count) {
      previous <- index - 1L
      syntax <- c(
        syntax,
        sprintf(
          "%s ~ %s*%s + %s*%s",
          factors$x[[index]], label("ar_x", previous), factors$x[[previous]],
          label("cl_yx", previous), factors$y[[previous]]
        ),
        sprintf(
          "%s ~ %s*%s + %s*%s",
          factors$y[[index]], label("ar_y", previous), factors$y[[previous]],
          label("cl_xy", previous), factors$x[[previous]]
        )
      )
    }
  } else if (identical(model_type, "ri_clpm")) {
    syntax <- c(
      paste0("RI_X =~ ", paste(paste0("1*", factors$x), collapse = " + ")),
      paste0("RI_Y =~ ", paste(paste0("1*", factors$y), collapse = " + ")),
      "RI_X ~~ RI_Y"
    )
    for (index in seq_len(wave_count)) {
      wx <- paste0("wx_", index)
      wy <- paste0("wy_", index)
      syntax <- c(
        syntax,
        paste0(wx, " =~ 1*", factors$x[[index]]),
        paste0(wy, " =~ 1*", factors$y[[index]]),
        paste0(factors$x[[index]], " ~~ 0*", factors$x[[index]]),
        paste0(factors$y[[index]], " ~~ 0*", factors$y[[index]]),
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
    return(lcm_sr_structural_syntax(
      factors,
      waves,
      constrained,
      growth_shape
    )$syntax)
  }
  syntax
}

latent_panel_path_rows <- function(fit, factors, model_type, confidence_level) {
  parameters <- lavaan::parameterEstimates(
    fit,
    standardized = TRUE,
    ci = TRUE,
    level = confidence_level
  )
  paths <- parameters[parameters$op == "~", , drop = FALSE]
  if (model_type %in% c("ri_clpm", "lcm_sr")) {
    x_names <- paste0("wx_", seq_along(factors$x))
    y_names <- paste0("wy_", seq_along(factors$y))
  } else {
    x_names <- factors$x
    y_names <- factors$y
  }
  wave_for <- c(setNames(seq_along(x_names), x_names), setNames(seq_along(y_names), y_names))
  construct_for <- c(
    setNames(rep("X", length(x_names)), x_names),
    setNames(rep("Y", length(y_names)), y_names)
  )
  paths <- paths[paths$lhs %in% names(wave_for) & paths$rhs %in% names(wave_for), , drop = FALSE]
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
      estimate = panel_finite(paths$est[[index]]),
      standardizedEstimate = panel_finite(paths$std.all[[index]]),
      standardError = panel_finite(paths$se[[index]]),
      statistic = panel_finite(paths$z[[index]]),
      pValue = panel_finite(paths$pvalue[[index]]),
      lower = panel_finite(paths$ci.lower[[index]]),
      upper = panel_finite(paths$ci.upper[[index]])
    )
  })
}

latent_panel_competing_row <- function(model_type, fit) {
  list(
    modelType = model_type,
    modelLabel = switch(
      model_type,
      ri_clpm = "潜变量 RI-CLPM",
      lcm_sr = "潜变量 LCM-SR",
      "潜变量 CLPM"
    ),
    converged = isTRUE(lavaan::lavInspect(fit, "converged")),
    fitIndices = panel_fit_indices(fit)
  )
}

fit_latent_longitudinal_panel <- function(data, spec, label_for, confidence_level = 0.95) {
  suppressPackageStartupMessages(library(lavaan))
  waves <- spec$waves
  item_map <- latent_panel_item_map(waves)
  item_ids <- unique(unlist(item_map, use.names = FALSE))
  missing_columns <- setdiff(c(spec$subjectVariableId, item_ids), names(data))
  if (length(missing_columns) > 0L) {
    stop(paste0("LONGITUDINAL_COLUMNS_NOT_FOUND: ", paste(missing_columns, collapse = ", ")))
  }
  if (anyDuplicated(data[[spec$subjectVariableId]][!is.na(data[[spec$subjectVariableId]])])) {
    stop("LONGITUDINAL_SUBJECT_ID_NOT_UNIQUE_FOR_WIDE_DATA")
  }
  analysis_data <- data[, item_ids, drop = FALSE]
  for (column in names(analysis_data)) {
    analysis_data[[column]] <- suppressWarnings(as.numeric(analysis_data[[column]]))
  }
  if (any(vapply(analysis_data, function(column) {
    finite <- column[is.finite(column)]
    length(finite) < 10L || length(unique(finite)) < 2L
  }, logical(1)))) {
    stop("LONGITUDINAL_ITEM_HAS_INSUFFICIENT_VARIATION")
  }

  requested_level <- if (identical(spec$invarianceLevel, "none")) {
    "configural"
  } else {
    spec$invarianceLevel
  }
  levels <- c("configural", "metric", "scalar", "strict")
  levels <- levels[seq_len(latent_panel_level_index(requested_level))]
  partial_positions <- unlist(spec$partialInvariancePositions, use.names = FALSE)
  measurement_fits <- list()
  measurement_rows <- list()
  measurement_warnings <- character(0)
  syntax_by_level <- list()
  for (level in levels) {
    measurement <- latent_panel_measurement_syntax(
      analysis_data,
      waves,
      level,
      spec$indicatorScale,
      partial_positions
    )
    fitted <- latent_panel_fit(
      measurement$syntax,
      analysis_data,
      spec,
      item_ids,
      identical(spec$indicatorScale, "ordinal")
    )
    if (!isTRUE(lavaan::lavInspect(fitted$fit, "converged"))) {
      stop(paste0("LONGITUDINAL_INVARIANCE_NONCONVERGENCE_", toupper(level)))
    }
    measurement_fits[[level]] <- fitted$fit
    syntax_by_level[[level]] <- measurement
    measurement_rows[[length(measurement_rows) + 1L]] <- latent_panel_invariance_row(
      level,
      fitted$fit
    )
    measurement_warnings <- c(measurement_warnings, fitted$warnings)
  }
  comparisons <- list()
  selected_level <- "configural"
  sequential_pass <- TRUE
  if (length(levels) > 1L) {
    for (index in 2:length(levels)) {
      comparison <- latent_panel_comparison(
        levels[[index - 1L]],
        levels[[index]],
        measurement_fits[[levels[[index - 1L]]]],
        measurement_fits[[levels[[index]]]]
      )
      comparisons[[length(comparisons) + 1L]] <- comparison
      sequential_pass <- sequential_pass && isTRUE(comparison$passesPracticalCriteria)
      if (sequential_pass) selected_level <- levels[[index]]
    }
  }

  selected_measurement <- syntax_by_level[[selected_level]]
  structural_types <- if (isTRUE(spec$compareCompetingModels)) {
    unique(c("clpm", "ri_clpm", if (length(waves) >= 5L) "lcm_sr"))
  } else {
    spec$modelType
  }
  structural_fits <- list()
  structural_syntaxes <- list()
  structural_warnings <- character(0)
  for (model_type in structural_types) {
    structural_syntax <- latent_panel_structural_syntax(
      selected_measurement$factors,
      model_type,
      isTRUE(spec$constrainAcrossTime),
      waves,
      spec$growthShape
    )
    structural_syntaxes[[model_type]] <- structural_syntax
    fitted <- latent_panel_fit(
      c(selected_measurement$syntax, structural_syntax),
      analysis_data,
      spec,
      item_ids,
      identical(spec$indicatorScale, "ordinal")
    )
    if (isTRUE(lavaan::lavInspect(fitted$fit, "converged"))) {
      structural_fits[[model_type]] <- fitted$fit
    }
    structural_warnings <- c(structural_warnings, fitted$warnings)
  }
  fit <- structural_fits[[spec$modelType]]
  if (is.null(fit)) stop("LONGITUDINAL_NONCONVERGENCE")

  parameter_table <- lavaan::parameterEstimates(fit)
  negative_variances <- parameter_table[
    parameter_table$op == "~~" &
      parameter_table$lhs == parameter_table$rhs &
      parameter_table$est < -1e-8,
    ,
    drop = FALSE
  ]
  post_check <- isTRUE(lavaan::lavInspect(fit, "post.check"))
  diagnostics <- lapply(unique(c(measurement_warnings, structural_warnings)), function(message) {
    list(code = "LAVAAN_WARNING", severity = "warning", message = message)
  })
  if (!identical(selected_level, requested_level)) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "LONGITUDINAL_INVARIANCE_NOT_SUPPORTED",
      severity = "warning",
      message = paste0(
        "请求的", requested_level, "等值性未通过预设实用标准；结构模型使用",
        selected_level, "等值约束。"
      )
    )
  }
  if (length(partial_positions) > 0L) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "PARTIAL_INVARIANCE_USER_SPECIFIED",
      severity = "info",
      message = paste0(
        "按用户事前指定释放部分等值位置：",
        paste(partial_positions, collapse = "、"),
        "。报告应说明理论依据。"
      )
    )
  }
  if (nrow(negative_variances) > 0L || !post_check) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "LATENT_PANEL_INVALID_SOLUTION",
      severity = "warning",
      message = "潜变量纵向模型存在负方差或后估计检查失败，路径仅用于诊断。"
    )
  }
  cmb_sensitivity <- if (identical(spec$cmbSensitivity, "global_ulmc")) {
    longitudinal_cmb_sensitivity(
      analysis_data,
      spec,
      item_ids,
      selected_measurement,
      structural_syntaxes[[spec$modelType]],
      fit,
      confidence_level,
      selected_level
    )
  } else {
    NULL
  }
  if (!is.null(cmb_sensitivity) && !isTRUE(cmb_sensitivity$validForInterpretation)) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "LONGITUDINAL_CMB_SENSITIVITY_INVALID",
      severity = "warning",
      message = "纵向共同方法偏差敏感性模型未通过解释门槛；主模型保留，但不得用该模块声称已排除 CMB。"
    )
  }

  wave_flow <- lapply(seq_along(waves), function(index) {
    wave_items <- c(item_map$x[[index]], item_map$y[[index]])
    observed <- rowSums(!is.na(analysis_data[, wave_items, drop = FALSE])) > 0L
    previous <- if (index == 1L) {
      rep(TRUE, nrow(analysis_data))
    } else {
      previous_items <- c(item_map$x[[index - 1L]], item_map$y[[index - 1L]])
      rowSums(!is.na(analysis_data[, previous_items, drop = FALSE])) > 0L
    }
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
    modelType = spec$modelType,
    modelLabel = switch(
      spec$modelType,
      ri_clpm = "潜变量 RI-CLPM",
      lcm_sr = "潜变量 LCM-SR",
      "潜变量 CLPM"
    ),
    measurementMode = "latent_items",
    subjectVariableId = spec$subjectVariableId,
    subjectLabel = label_for(spec$subjectVariableId),
    constructLabels = list(x = "X 潜变量", y = "Y 潜变量"),
    waveCount = length(waves),
    sampleSize = as.integer(lavaan::lavInspect(fit, "ntotal")),
    estimator = spec$estimator,
    missingMethod = spec$missing,
    constrainedAcrossTime = isTRUE(spec$constrainAcrossTime),
    fitIndices = panel_fit_indices(fit),
    paths = latent_panel_path_rows(
      fit,
      selected_measurement$factors,
      spec$modelType,
      confidence_level
    ),
    waveSampleFlow = wave_flow,
    measurementInvariance = list(
      requestedLevel = requested_level,
      selectedLevel = selected_level,
      indicatorScale = spec$indicatorScale,
      partialPositions = as.list(partial_positions),
      models = measurement_rows,
      comparisons = comparisons,
      criteriaSource = "Chen (2007) practical fit-index change criteria"
    ),
    competingModels = lapply(names(structural_fits), function(model_type) {
      latent_panel_competing_row(model_type, structural_fits[[model_type]])
    }),
    growthModel = if (identical(spec$modelType, "lcm_sr")) {
      lcm_sr_result(fit, spec, confidence_level)
    } else {
      NULL
    },
    cmbSensitivity = cmb_sensitivity,
    diagnostics = diagnostics,
    validForInterpretation = post_check &&
      nrow(negative_variances) == 0L &&
      latent_panel_level_index(selected_level) >= latent_panel_level_index("metric"),
    causalNotice = "潜变量交叉滞后路径控制测量误差并提供时间方向证据；观察性设计仍不能自动识别因果效应。",
    provenance = list(
      engine = "R lavaan",
      engineVersion = as.character(packageVersion("lavaan")),
      estimand = if (identical(spec$modelType, "ri_clpm")) {
        "latent within-person autoregressive and cross-lagged association"
      } else if (identical(spec$modelType, "lcm_sr")) {
        "structured residual dynamics net of latent growth trajectory"
      } else {
        "latent autoregressive and cross-lagged association"
      },
      measurementInvariance = selected_level
    )
  )
  if (isTRUE(spec$runRobustnessChecks)) {
    result$robustnessChecks <- list(panel_result_scenario("主模型", result))
    constraint_spec <- spec
    constraint_spec$constrainAcrossTime <- !isTRUE(spec$constrainAcrossTime)
    constraint_spec$compareCompetingModels <- FALSE
    constraint_spec$runRobustnessChecks <- FALSE
    constraint_spec$powerAnalysis <- NULL
    constraint_spec$cmbSensitivity <- "none"
    constraint_result <- tryCatch(
      fit_latent_longitudinal_panel(
        data,
        constraint_spec,
        label_for,
        confidence_level
      ),
      error = function(error) NULL
    )
    if (!is.null(constraint_result)) {
      result$robustnessChecks[[length(result$robustnessChecks) + 1L]] <-
        panel_result_scenario("切换跨时路径等值约束", constraint_result)
    }
    if (anyNA(analysis_data) && !identical(spec$estimator, "WLSMV")) {
      missing_spec <- spec
      missing_spec$missing <- if (identical(spec$missing, "fiml")) {
        "complete_cases"
      } else {
        "fiml"
      }
      missing_spec$compareCompetingModels <- FALSE
      missing_spec$runRobustnessChecks <- FALSE
      missing_spec$powerAnalysis <- NULL
      missing_spec$cmbSensitivity <- "none"
      missing_result <- tryCatch(
        fit_latent_longitudinal_panel(
          data,
          missing_spec,
          label_for,
          confidence_level
        ),
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
