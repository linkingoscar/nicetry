run_questionnaire_measurement <- function() {
  model_type <- spec$modelType
  required_packages <- unique(c(
    if (model_type %in% c("reliability", "cfa", "measurement_invariance", "bifactor", "esem_bifactor_irt", "ulmc", "common_method_bias")) "lavaan" else character(0),
    if (model_type %in% c("irt", "esem_bifactor_irt")) "mirt" else character(0),
    if (model_type %in% c("esem", "esem_bifactor_irt")) "psych" else character(0)
  ))
  missing_packages <- required_packages[!vapply(required_packages, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing_packages) > 0) stop(paste0("MEASUREMENT_PACKAGE_NOT_INSTALLED: ", paste(missing_packages, collapse = ",")))

  data <- read_analysis_data()
  item_ids <- unique(unlist(spec$itemIds, use.names = FALSE))
  missing_columns <- setdiff(item_ids, names(data))
  if (length(missing_columns) > 0) stop(paste0("MEASUREMENT_COLUMN_NOT_FOUND: ", paste(missing_columns, collapse = ",")))
  constructs <- lapply(spec$constructs, function(construct) {
    list(
      id = construct$id,
      label = construct$label,
      itemIds = as.list(intersect(unlist(construct$itemIds, use.names = FALSE), item_ids)),
      scoreId = if (is.null(construct$scoreId)) NULL else construct$scoreId
    )
  })
  item_frame <- data[, item_ids, drop = FALSE]
  for (item_id in item_ids) item_frame[[item_id]] <- suppressWarnings(as.numeric(item_frame[[item_id]]))
  item_frame <- item_frame[complete.cases(item_frame), , drop = FALSE]
  if (nrow(item_frame) < 20) stop("MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS")

  reliability_result <- NULL
  efa_result <- NULL
  cfa_result <- NULL
  invariance_result <- NULL
  bifactor_result <- NULL
  esem_result <- NULL
  irt_result <- NULL
  cmb_result <- NULL
  if (identical(model_type, "reliability")) {
    reliability_result <- list(
      available = TRUE,
      constructs = lapply(constructs, function(construct) {
        ids <- intersect(unlist(construct$itemIds, use.names = FALSE), names(item_frame))
        metrics <- calc_ordinal_reliability(item_frame, ids)
        item_diag <- calc_item_diagnostics(item_frame, ids)
        c(list(constructId = construct$id, itemIds = as.list(ids), itemAnalysis = item_diag), metrics)
      }),
      structuralMissingness = calc_structural_missingness(data, constructs)
    )
  }
  if (identical(model_type, "efa")) {
    correlation <- if (identical(spec$itemScale, "ordinal")) {
      tryCatch(lavaan::lavCor(item_frame, ordered = names(item_frame)), error = function(error) NULL)
    } else {
      stats::cor(item_frame, use = "pairwise.complete.obs")
    }
    if (is.null(correlation)) stop("MEASUREMENT_CORRELATION_ESTIMATION_FAILED")
    if (any(!is.finite(correlation))) stop("MEASUREMENT_CORRELATION_NOT_FINITE")
    map_result <- run_map_test(correlation)
    factor_count <- min(as.integer(spec$factorCount), ncol(item_frame) - 1L)
    extraction_method <- if (is.null(spec$extractionMethod)) "ml" else spec$extractionMethod
    efa_res <- tryCatch(
      run_efa_with_method(
        data = item_frame,
        correlation = correlation,
        n_obs = nrow(item_frame),
        factor_count = factor_count,
        method = extraction_method,
        rotation = spec$rotation,
        item_scale = if (is.null(spec$itemScale)) "continuous" else spec$itemScale
      ),
      error = function(e) stop(paste0("MEASUREMENT_EFA_ESTIMATION_FAILED: ", conditionMessage(e)))
    )
    loading_matrix <- efa_res$loadings
    factor_correlations <- efa_res$factorCorrelations
    efa_result <- list(
      available = TRUE,
      method = efa_res$extractionMethod,
      correlationType = efa_res$correlationType,
      requestedFactorCount = as.integer(spec$factorCount),
      factorCount = factor_count,
      rotation = spec$rotation,
      map = map_result,
      parallelAnalysis = if (nrow(item_frame) >= 10 && ncol(item_frame) >= 3) run_parallel_analysis(item_frame, as.integer(spec$parallelIterations), as.integer(spec$seed)) else NULL,
      loadings = lapply(seq_len(nrow(loading_matrix)), function(index) list(itemId = rownames(loading_matrix)[[index]], loadings = as.list(as.numeric(loading_matrix[index, ])))),
      factorCorrelations = mat_to_list(factor_correlations),
      diagnostics = efa_res$diagnostics,
      splitValidation = run_split_validation(item_frame, factor_count, spec$rotation, as.integer(spec$seed))
    )
  }
  if (identical(model_type, "cfa")) {
    ordered_items <- if (identical(spec$itemScale, "ordinal")) item_ids else NULL
    cfa_result <- fit_lavaan_cfa(item_frame, constructs, estimator = spec$estimator, ordered_items = ordered_items)
    if (!isTRUE(cfa_result$available)) stop(paste0("MEASUREMENT_CFA_ESTIMATION_FAILED: ", cfa_result$reason))
    validity_bundle <- tryCatch(calc_cfa_validity_bundle(cfa_result, constructs, item_frame), error = function(e) list(available = FALSE, reason = conditionMessage(e)))
    cfa_result$validity <- validity_bundle
  }
  if (identical(model_type, "measurement_invariance")) {
    group_id <- spec$groupVariableId
    if (is.null(group_id) || !group_id %in% names(data)) stop("MEASUREMENT_INVARIANCE_GROUP_REQUIRED")
    invariance_data <- data[, unique(c(item_ids, group_id)), drop = FALSE]
    for (item_id in item_ids) invariance_data[[item_id]] <- suppressWarnings(as.numeric(invariance_data[[item_id]]))
    syntax <- paste(vapply(constructs, function(construct) paste0("F_", construct$id, " =~ ", paste(unlist(construct$itemIds, use.names = FALSE), collapse = " + ")), character(1)), collapse = "\n")
    group_partial <- if (is.null(spec$partialReleasedParameters)) NULL else unlist(spec$partialReleasedParameters, use.names = FALSE)
    invariance_result <- run_measurement_invariance(invariance_data, syntax, group_id, estimator = spec$estimator, group_partial = group_partial)
    if (!isTRUE(invariance_result$available)) stop(paste0("MEASUREMENT_INVARIANCE_ESTIMATION_FAILED: ", invariance_result$reason))
    selected_levels <- unique(unlist(spec$invarianceLevels, use.names = FALSE))
    invariance_result$models <- invariance_result$models[names(invariance_result$models) %in% selected_levels]
    invariance_result$comparisons <- invariance_result$comparisons[names(invariance_result$comparisons) %in% selected_levels]
  }
  if (model_type %in% c("bifactor", "esem_bifactor_irt")) {
    bifactor_result <- tryCatch(fit_bifactor_model(item_frame, constructs), error = function(error) list(available = FALSE, reason = conditionMessage(error)))
  }
  if (model_type %in% c("esem", "esem_bifactor_irt")) {
    esem_result <- tryCatch(fit_esem_model(item_frame, constructs, factor_count = as.integer(spec$factorCount)), error = function(error) list(available = FALSE, reason = conditionMessage(error)))
  }
  if (model_type %in% c("irt", "esem_bifactor_irt")) {
    group_values <- if (!is.null(spec$groupVariableId) && spec$groupVariableId %in% names(data)) data[[spec$groupVariableId]] else NULL
    irt_result <- tryCatch(fit_irt_dif_model(item_frame, constructs, group_values), error = function(error) list(available = FALSE, reason = conditionMessage(error)))
  }
  if (model_type %in% c("common_method_bias", "marker_variable", "ulmc")) {
    marker_result <- if (model_type %in% c("common_method_bias", "marker_variable")) {
      tryCatch(calc_marker_variable_cmb(data, spec$markerVariableId, constructs), error = function(error) list(available = FALSE, reason = conditionMessage(error)))
    } else NULL
    ulmc_result <- if (model_type %in% c("common_method_bias", "ulmc")) {
      tryCatch(fit_ulmc_cmb_model(item_frame, constructs), error = function(error) list(available = FALSE, reason = conditionMessage(error)))
    } else NULL
    cmb_result <- list(markerVariable = marker_result, ulmc = ulmc_result)
  }

  warnings <- list(message_entry("MEASUREMENT_COMPLETE_CASES", "info", "高级测量结果使用声明题项的完整案例；题项级缺失计数保留在样本流中。"))
  if (!is.null(cmb_result)) warnings[[length(warnings) + 1L]] <- message_entry("COMMON_METHOD_DIAGNOSTIC", "warning", "共同方法偏差检验是诊断证据，不自动等同于结论失效。")
  list(
    sampleFlow = list(original = nrow(data), included = nrow(item_frame), excluded = nrow(data) - nrow(item_frame), missingMethod = "complete_cases"),
    estimates = list(),
    diagnostics = list(message_entry("MEASUREMENT_RUN_COMPLETED", "info", sprintf("Completed questionnaire measurement slice %s", model_type))),
    warnings = warnings,
    provenance = list(
      engine = "ResearchPath R questionnaire measurement engine",
      engineVersion = "0.1.0",
      softwareVersions = as.list(c(jsonlite = as.character(packageVersion("jsonlite")), setNames(vapply(required_packages, function(package) as.character(packageVersion(package)), character(1)), required_packages))),
      estimand = "declared questionnaire measurement structure and item-level diagnostics",
      degreesOfFreedomMethod = "model-specific"
    ),
    familyResult = list(
      family = family,
      modelType = model_type,
      sampleSize = nrow(item_frame),
      itemCount = length(item_ids),
      constructCount = length(constructs),
      reliability = reliability_result,
      efa = efa_result,
      cfa = cfa_result,
      invariance = invariance_result,
      bifactor = bifactor_result,
      esem = esem_result,
      irt = irt_result,
      commonMethodBias = cmb_result
    )
  )
}
