write_progress("confirmatory_factor_analysis", 0.58)
check_cancel()
cfa_bundle <- run_empirical_cfa(item_complete, metadata$constructs, item_ids, variable_lookup)
cfa <- cfa_bundle$cfa; measurement_sample_adequacy <- cfa_bundle$sampleAdequacy
passes_confirmatory_guardrail <- cfa_bundle$passes
estimated_parameter_count <- cfa_bundle$estimatedParameterCount
cases_per_parameter <- cfa_bundle$casesPerParameter
measurement_item_scale <- cfa_bundle$itemScale
if (non_iid_context) {
  passes_confirmatory_guardrail <- FALSE
  cfa$validForConfirmatoryInterpretation <- FALSE
  cfa$clusterAdjustment <- "none_descriptive_measurement_preparation_only"
  if (!is.null(cfa$methodExecution)) {
    cfa$methodExecution$interpretationBoundary <- paste0(
      cfa$methodExecution$interpretationBoundary,
      " 当前数据行非独立；本次未使用多层/纵向 CFA 或依赖结构稳健推断，因此拟合与载荷只作测量准备。"
    )
  }
  measurement_sample_adequacy$status <- "caution"
  measurement_sample_adequacy$interpretation <- paste0(
    measurement_sample_adequacy$interpretation,
    " 当前数据存在聚类或重复测量，案例数护栏不能替代多层/纵向测量模型。"
  )
  cfa$sampleAdequacy <- measurement_sample_adequacy
}
