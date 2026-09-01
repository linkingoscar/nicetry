researchpath_build_empirical_warnings <- function(state) {
  warnings <- list(
    list(code = "ASSOCIATIONAL_ONLY", severity = "warning", message = "横截面问卷结果默认按关联性证据解释，不自动生成因果结论。"),
    list(code = "THRESHOLDS_REQUIRE_JUDGMENT", severity = "warning", message = "α、ω、KMO、载荷、CR、AVE 与拟合指数不使用单一阈值自动判定，需结合理论和样本条件。"),
    list(code = "COMMON_METHOD_DIAGNOSTIC", severity = "warning", message = "Harman 单因子仅为描述性诊断，不能单独排除共同方法偏差。"),
    list(code = "MULTIPLICITY_FAMILY_REGISTERED", severity = "info", message = paste0("相关、组间比较、回归与假设统一登记到 multiplicity family ", state$multiplicity_family_id, "；当前各组件仍保留各自检验程序，不能把调整后 p 值跨组件直接互换。"))
  )
  if (state$nested_context) warnings[[length(warnings) + 1L]] <- list(
    code = "NESTED_BASE_REPORT_DESCRIPTIVE_ONLY", severity = "warning",
    message = "nested 横截面基础报告仅执行描述、测量准备和聚合诊断；逐行相关 p 值/区间、普通组间检验、单层回归、响应面和普通 HTMT bootstrap 未执行。"
  )
  if (state$repeated_context) warnings[[length(warnings) + 1L]] <- list(
    code = "REPEATED_BASE_REPORT_DESCRIPTIVE_ONLY", severity = "warning",
    message = "纵向/密集追踪基础报告不运行逐行横截面推断；相关 p 值/区间、普通组间检验、单层回归、响应面、测量等值性和普通 HTMT bootstrap 未执行。"
  )
  if (!state$passes_confirmatory_guardrail) warnings[[length(warnings) + 1L]] <- list(
    code = "CFA_SAMPLE_ADEQUACY_GUARDRAIL", severity = "warning",
    message = paste0("CFA 完整案例 N=", nrow(state$item_complete), "，估计自由参数约 ", state$estimated_parameter_count,
      "（每参数 ", if (is.finite(state$cases_per_parameter)) round(state$cases_per_parameter, 2) else "—",
      " 个案例），未达到平台保守解释护栏（N≥100 且每自由参数≥5）。",
      "该护栏不是通用样本量定理；当前测量结果仅宜作探索或流程演示。")
  )
  if (!is.null(state$longitudinal_panel)) {
    warnings[[length(warnings) + 1L]] <- list(code = "LONGITUDINAL_ASSOCIATION_NOT_CAUSATION", severity = "warning", message = state$longitudinal_panel$causalNotice)
    for (diagnostic in state$longitudinal_panel$diagnostics) warnings[[length(warnings) + 1L]] <- diagnostic
  }
  if (!is.null(state$diary_multilevel)) {
    warnings[[length(warnings) + 1L]] <- list(code = "MULTILEVEL_LEVELS_REQUIRE_SEPARATE_INTERPRETATION", severity = "warning", message = "日记模型的 within-person 与 between-person 效应属于不同估计对象，不能互相替代。")
    for (diagnostic in state$diary_multilevel$diagnostics) warnings[[length(warnings) + 1L]] <- diagnostic
  }
  if (!is.null(state$parallel_fallback_reason)) warnings[[length(warnings) + 1L]] <- list(code = "PARALLEL_ANALYSIS_FALLBACK", severity = "warning", message = state$parallel_fallback_reason)
  parallel_zero_warning <- parallel_analysis_zero_warning(state$factor_method, state$parallel_res)
  if (!is.null(parallel_zero_warning)) warnings[[length(warnings) + 1L]] <- parallel_zero_warning
  if (!is.null(state$hierarchical_regression) && isTRUE(state$hierarchical_regression$underdetermined)) warnings[[length(warnings) + 1L]] <- underdetermined_regression_warning(state$hierarchical_regression$n)
  if (!is.null(state$hierarchical_regression) && !isTRUE(state$hierarchical_regression$robustness$hc3Execution$available)) warnings[[length(warnings) + 1L]] <- list(
    code = "HC3_UNAVAILABLE_NOT_PUBLICATION_PRIMARY", severity = "warning",
    message = paste0("HC3 敏感性估计不可用（", state$hierarchical_regression$robustness$hc3Execution$fallbackReason, "）；未执行 classical 替代，回归结果不得作为论文主分析自动发布。")
  )
  if (length(state$partial_undefined_pairs) > 0L) warnings[[length(warnings) + 1L]] <- partial_correlation_undefined_warning(state$partial_undefined_pairs)
  if (length(state$htmt_undefined_pairs) > 0L) warnings[[length(warnings) + 1L]] <- htmt_undefined_warning(state$htmt_undefined_pairs)
  if (!isTRUE(state$htmt_available) && !is.null(state$htmt_reason)) warnings[[length(warnings) + 1L]] <- list(code = "HTMT_NOT_RUN_FOR_DECLARED_ITEM_SCALE", severity = "warning", message = paste0("HTMT 未运行：", state$htmt_reason, "。平台没有静默改用 Pearson 相关。"))
  if (!is.null(state$kmo_skipped_reason)) warnings[[length(warnings) + 1L]] <- list(code = "KMO_SKIPPED_RESOURCE_BUDGET", severity = "warning", message = state$kmo_skipped_reason)
  if (!is.null(state$group_comparison)) {
    skipped <- Filter(function(row) isTRUE(row$unavailable), state$group_comparison$results)
    if (length(skipped) > 0L) warnings[[length(warnings) + 1L]] <- list(code = "GROUP_COMPARISON_SKIPPED", severity = "warning", message = sprintf("以下变量的组间比较因样本不足或组内零方差被跳过：%s。", paste(vapply(skipped, function(row) row$label, character(1)), collapse = "、")))
  }
  if (isTRUE(state$htmt_ci$invalidReplicationCount > 0L)) warnings[[length(warnings) + 1L]] <- list(
    code = "HTMT_REPLICATION_DROPPED", severity = "warning",
    message = sprintf("HTMT 置信区间 bootstrap 中 %d 次重抽样拟合失败被剔除（涉及 %d 对构念，占重抽样数的 %.1f%%），区间基于剩余有效重抽样计算。", state$htmt_ci$invalidReplicationCount, state$htmt_ci$affectedPairs, 100 * state$htmt_ci$invalidReplicationCount / max(1L, as.integer(state$htmt_ci$replicates)))
  )
  if (isTRUE(state$efa$methodExecution$fallbackApplied)) warnings[[length(warnings) + 1L]] <- measurement_fallback_warning(state$efa$methodExecution, "最大似然 EFA 拟合失败，已改用 PCA")
  if (isTRUE(state$cfa$methodExecution$fallbackApplied)) warnings[[length(warnings) + 1L]] <- measurement_fallback_warning(state$cfa$methodExecution, "lavaan CFA 未返回可用结果，已显式回退到自研正态理论 ML 简单结构拟合器")
  if (!isTRUE(state$cfa$available)) warnings[[length(warnings) + 1L]] <- list(code = "CFA_UNAVAILABLE", severity = "warning", message = state$cfa$reason)
  if (isTRUE(state$validity$methodExecution$fallbackApplied)) warnings[[length(warnings) + 1L]] <- measurement_fallback_warning(state$validity$methodExecution, "CFA 载荷不完整，CR、AVE 与 Fornell–Larcker 对角线已使用单因子特征分解近似")
  if (isTRUE(state$cfa$available) && !isTRUE(state$cfa$converged)) warnings[[length(warnings) + 1L]] <- list(code = "CFA_NOT_CONVERGED", severity = "warning", message = "CFA 优化未正常收敛，相关载荷和拟合指标仅供诊断。")
  for (construct in state$construct_validity) {
    loadings <- unlist(construct$standardizedLoadings); finite_loadings <- loadings[is.finite(loadings)]
    if (any(finite_loadings < 0) && any(finite_loadings > 0)) warnings[[length(warnings) + 1L]] <- list(
      code = paste0("MIXED_SIGN_LOADINGS_", construct$constructId), severity = "warning",
      message = paste0("构念“", construct$label, "”存在正负混合载荷；请检查反向计分、题项方向和模型设定。")
    )
  }
  if (!is.null(state$procedure)) {
    suppress_codes <- c("MULTIPLICITY_FAMILY_REGISTERED")
    if (!identical(state$procedure, "common_method")) suppress_codes <- c(suppress_codes, "COMMON_METHOD_DIAGNOSTIC")
    if (!state$procedure %in% c("cfa", "validity")) suppress_codes <- c(suppress_codes, "CFA_UNAVAILABLE", "CFA_SAMPLE_ADEQUACY_GUARDRAIL")
    if (!state$procedure %in% c("efa", "cfa", "validity", "reliability")) suppress_codes <- c(suppress_codes, "THRESHOLDS_REQUIRE_JUDGMENT")
    warnings <- Filter(function(w) !w$code %in% suppress_codes, warnings)
  }
  warnings
}
