assess_measurement_sample_adequacy <- function(item_complete, constructs, cfa_result) {
  item_count <- ncol(item_complete)
  approximate_parameter_count <- if (item_count > 0) {
    as.integer(2 * item_count + length(constructs) * (length(constructs) - 1) / 2)
  } else {
    0L
  }
  fitted_parameter_count <- cfa_result$estimatedParameterCount
  estimated_parameter_count <- if (!is.null(fitted_parameter_count)) {
    as.integer(fitted_parameter_count)
  } else {
    approximate_parameter_count
  }
  cases_per_parameter <- if (estimated_parameter_count > 0) {
    nrow(item_complete) / estimated_parameter_count
  } else {
    NA_real_
  }

  # A conservative and transparent reporting guardrail, not a universal
  # theorem about CFA sample size. Its purpose is to stop a computable small-N
  # solution from being presented as stable confirmatory evidence.
  passes <- (
    nrow(item_complete) >= 100
      && is.finite(cases_per_parameter)
      && cases_per_parameter >= 5
  )
  evidence <- list(
    status = if (passes) "adequate" else "caution",
    completeCases = nrow(item_complete),
    itemCount = item_count,
    estimatedParameterCount = estimated_parameter_count,
    casesPerParameter = finite_number(cases_per_parameter),
    minimumCompleteCasesGuardrail = 100L,
    minimumCasesPerParameterGuardrail = 5,
    parameterCountSource = if (!is.null(fitted_parameter_count)) {
      "fitted model free-parameter count"
    } else {
      "simple-structure approximation: 2p + k(k-1)/2"
    },
    interpretation = if (passes) {
      paste0(
        "达到平台的保守确认性解释护栏；仍须结合模型复杂度、估计量、",
        "数据分布与收敛诊断判断。"
      )
    } else {
      paste0(
        "未达到平台的保守确认性解释护栏；结果可用于探索和流程演示，",
        "不宜据此作稳定的确认性测量结论。"
      )
    },
    ruleNature = "transparent platform guardrail, not a universal sample-size threshold"
  )
  cfa_result$sampleAdequacy <- evidence
  cfa_result$casesPerParameter <- finite_number(cases_per_parameter)
  cfa_result$validForConfirmatoryInterpretation <- (
    isTRUE(cfa_result$available)
      && isTRUE(cfa_result$converged)
      && passes
  )
  list(
    cfa = cfa_result,
    evidence = evidence,
    passes = passes,
    estimatedParameterCount = estimated_parameter_count,
    casesPerParameter = cases_per_parameter
  )
}
