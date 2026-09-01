longitudinal_cmb_blocked <- function(code, message) {
  list(
    requested = TRUE,
    available = FALSE,
    validForInterpretation = FALSE,
    method = "Global orthogonal unmeasured latent method factor",
    diagnostics = list(list(code = code, severity = "warning", message = message))
  )
}

longitudinal_cmb_identification <- function(fit) {
  parameters <- lavaan::parameterEstimates(fit)
  negative_variances <- parameters[
    parameters$op == "~~" &
      parameters$lhs == parameters$rhs &
      parameters$est < -1e-8,
    ,
    drop = FALSE
  ]
  latent_covariance <- tryCatch(
    lavaan::lavInspect(fit, "cov.lv"),
    error = function(error) NULL
  )
  covariance_eigen <- if (is.null(latent_covariance)) {
    numeric(0)
  } else {
    eigen(
      (latent_covariance + t(latent_covariance)) / 2,
      symmetric = TRUE,
      only.values = TRUE
    )$values
  }
  information <- tryCatch(
    lavaan::lavInspect(fit, "information"),
    error = function(error) NULL
  )
  information_eigen <- if (is.null(information)) {
    numeric(0)
  } else {
    eigen((information + t(information)) / 2, symmetric = TRUE, only.values = TRUE)$values
  }
  information_ratio <- if (
    length(information_eigen) &&
    max(abs(information_eigen)) > 0
  ) {
    min(information_eigen) / max(abs(information_eigen))
  } else {
    NA_real_
  }
  converged <- isTRUE(lavaan::lavInspect(fit, "converged"))
  post_check <- isTRUE(lavaan::lavInspect(fit, "post.check"))
  covariance_minimum <- if (length(covariance_eigen)) min(covariance_eigen) else NA_real_
  list(
    converged = converged,
    postCheckPassed = post_check,
    negativeVarianceCount = nrow(negative_variances),
    latentCovarianceMinimumEigenvalue = panel_finite(covariance_minimum),
    informationMinimumEigenvalueRatio = panel_finite(information_ratio),
    informationFullRank = is.finite(information_ratio) && information_ratio > 1e-10,
    valid = converged &&
      post_check &&
      nrow(negative_variances) == 0L &&
      is.finite(covariance_minimum) &&
      covariance_minimum > -1e-8 &&
      is.finite(information_ratio) &&
      information_ratio > 1e-10
  )
}

longitudinal_cmb_path_changes <- function(
  baseline_fit,
  method_fit,
  factors,
  model_type,
  confidence_level
) {
  baseline <- latent_panel_path_rows(
    baseline_fit,
    factors,
    model_type,
    confidence_level
  )
  adjusted <- latent_panel_path_rows(
    method_fit,
    factors,
    model_type,
    confidence_level
  )
  adjusted_lookup <- setNames(adjusted, vapply(adjusted, function(row) row$id, character(1)))
  rows <- lapply(baseline, function(row) {
    comparison <- adjusted_lookup[[row$id]]
    if (is.null(comparison)) return(NULL)
    baseline_significant <- !is.null(row$pValue) && row$pValue < 0.05
    adjusted_significant <- !is.null(comparison$pValue) && comparison$pValue < 0.05
    list(
      id = row$id,
      pathType = row$pathType,
      direction = row$direction,
      fromWave = row$fromWave,
      toWave = row$toWave,
      baselineEstimate = row$estimate,
      adjustedEstimate = comparison$estimate,
      absoluteChange = panel_finite(comparison$estimate - row$estimate),
      relativeChange = if (!is.null(row$estimate) && abs(row$estimate) > 1e-12) {
        panel_finite((comparison$estimate - row$estimate) / abs(row$estimate))
      } else {
        NULL
      },
      baselinePValue = row$pValue,
      adjustedPValue = comparison$pValue,
      signChanged = !is.null(row$estimate) &&
        !is.null(comparison$estimate) &&
        sign(row$estimate) != sign(comparison$estimate),
      inferenceChanged = baseline_significant != adjusted_significant,
      adjustedLower = comparison$lower,
      adjustedUpper = comparison$upper
    )
  })
  Filter(Negate(is.null), rows)
}

longitudinal_cmb_sensitivity <- function(
  analysis_data,
  spec,
  item_ids,
  selected_measurement,
  structural_syntax,
  baseline_fit,
  confidence_level,
  selected_level
) {
  if (latent_panel_level_index(selected_level) < latent_panel_level_index("scalar")) {
    return(longitudinal_cmb_blocked(
      "CMB_REQUIRES_SCALAR_INVARIANCE",
      "全局方法因子敏感性分析要求结构模型至少建立在标量等值测量模型上。"
    ))
  }
  substantive_latents <- lavaan::lavNames(baseline_fit, type = "lv")
  loading_terms <- c(
    paste0("1*", item_ids[[1]]),
    vapply(seq_along(item_ids[-1]), function(index) {
      paste0("cm_", index + 1L, "*", item_ids[[index + 1L]])
    }, character(1))
  )
  method_syntax <- c(
    paste0("METHOD =~ ", paste(loading_terms, collapse = " + ")),
    paste0("METHOD ~~ 0*", substantive_latents),
    "METHOD ~ 0*1"
  )
  fitted <- tryCatch(
    latent_panel_fit(
      c(selected_measurement$syntax, structural_syntax, method_syntax),
      analysis_data,
      spec,
      item_ids,
      FALSE
    ),
    error = function(error) error
  )
  if (inherits(fitted, "error")) {
    return(longitudinal_cmb_blocked(
      "CMB_MODEL_ESTIMATION_FAILED",
      paste0("全局方法因子模型估计失败：", conditionMessage(fitted))
    ))
  }
  fit <- fitted$fit
  identification <- longitudinal_cmb_identification(fit)
  parameters <- lavaan::parameterEstimates(fit, standardized = TRUE)
  loadings <- parameters[
    parameters$lhs == "METHOD" & parameters$op == "=~",
    ,
    drop = FALSE
  ]
  loading_rows <- lapply(seq_len(nrow(loadings)), function(index) {
    list(
      itemId = as.character(loadings$rhs[[index]]),
      loading = panel_finite(loadings$est[[index]]),
      standardizedLoading = panel_finite(loadings$std.all[[index]]),
      standardizedVarianceShare = panel_finite(loadings$std.all[[index]]^2),
      pValue = panel_finite(loadings$pvalue[[index]])
    )
  })
  variance_shares <- vapply(
    loading_rows,
    function(row) if (is.null(row$standardizedVarianceShare)) NA_real_ else row$standardizedVarianceShare,
    numeric(1)
  )
  path_changes <- longitudinal_cmb_path_changes(
    baseline_fit,
    fit,
    selected_measurement$factors,
    spec$modelType,
    confidence_level
  )
  diagnostics <- lapply(fitted$warnings, function(message) {
    list(code = "CMB_LAVAAN_WARNING", severity = "warning", message = message)
  })
  if (!isTRUE(identification$valid)) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "CMB_IDENTIFICATION_FAILED",
      severity = "warning",
      message = "方法因子模型未通过正定性、信息矩阵、负方差或后估计检查，不得据此宣称已排除共同方法偏差。"
    )
  }
  list(
    requested = TRUE,
    available = TRUE,
    validForInterpretation = isTRUE(identification$valid),
    method = "Global orthogonal unmeasured latent method factor",
    orthogonalToSubstantiveFactors = TRUE,
    markerItemId = item_ids[[1]],
    indicatorCount = length(item_ids),
    identification = identification,
    baselineFitIndices = panel_fit_indices(baseline_fit),
    methodFactorFitIndices = panel_fit_indices(fit),
    methodLoadings = loading_rows,
    averageStandardizedVarianceShare = if (all(is.na(variance_shares))) {
      NULL
    } else {
      panel_finite(mean(variance_shares, na.rm = TRUE))
    },
    pathChanges = path_changes,
    changedInferenceCount = sum(vapply(
      path_changes,
      function(row) isTRUE(row$inferenceChanged),
      logical(1)
    )),
    diagnostics = diagnostics,
    interpretation = paste0(
      "该结果是识别敏感性分析，而非共同方法偏差不存在的证明；应结合程序性控制、",
      "标记变量或多源数据共同判断。"
    )
  )
}
