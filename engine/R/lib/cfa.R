build_cfa_execution <- function(
  requested_method,
  executed_method,
  fallback_applied = FALSE,
  fallback_code = NULL,
  fallback_reason = NULL,
  affected_outputs = list(),
  interpretation_boundary = NULL
) {
  list(
    requestedMethod = requested_method,
    executedMethod = executed_method,
    fallbackApplied = isTRUE(fallback_applied),
    fallbackCode = fallback_code,
    fallbackReason = fallback_reason,
    affectedOutputs = affected_outputs,
    interpretationBoundary = interpretation_boundary
  )
}

cfa_positive_definiteness <- function(post_check) {
  if (isTRUE(post_check)) return("positive_definite")
  if (identical(post_check, FALSE)) return("not_positive_definite")
  "unknown"
}

classify_measurement_item_scale <- function(item_ids, variable_lookup) {
  item_types <- vapply(item_ids, function(item_id) {
    if (is.null(variable_lookup[[item_id]]$type)) "continuous" else variable_lookup[[item_id]]$type
  }, character(1))
  ordinal <- item_types %in% c("ordinal", "likert")
  if (length(item_types) > 0L && all(ordinal)) {
    "ordinal"
  } else if (any(ordinal)) {
    "mixed"
  } else {
    "continuous"
  }
}

run_empirical_cfa <- function(items, constructs, item_ids, variable_lookup) {
  annotate_cfa_publication <- function(cfa_result, passes) {
    reason_codes <- character(0)
    if (!isTRUE(cfa_result$available)) reason_codes <- c(reason_codes, "CFA_UNAVAILABLE")
    if (!isTRUE(cfa_result$converged)) reason_codes <- c(reason_codes, "CFA_NOT_CONVERGED")
    if (isTRUE(cfa_result$methodExecution$fallbackApplied)) reason_codes <- c(reason_codes, "CFA_NUMERICAL_FALLBACK")
    if (isTRUE(cfa_result$hasHeywoodCase)) reason_codes <- c(reason_codes, "CFA_HEYWOOD_CASE")
    if (isTRUE(cfa_result$notPositiveDefinite)) reason_codes <- c(reason_codes, "CFA_NOT_POSITIVE_DEFINITE")
    if (!isTRUE(passes)) reason_codes <- c(reason_codes, "CFA_SAMPLE_ADEQUACY_GUARDRAIL")
    cfa_result$publicationEligible <- length(reason_codes) == 0L
    cfa_result$requiresManualReview <- length(reason_codes) > 0L
    cfa_result$publicationEligibilityReasons <- as.list(reason_codes)
    cfa_result
  }
  item_scale <- classify_measurement_item_scale(item_ids, variable_lookup)
  if (identical(item_scale, "mixed")) {
    fitted <- list(
      available = FALSE,
      converged = FALSE,
      reason = "MIXED_SCALE_CFA_REQUIRES_EXPLICIT_MIXED_CORRELATION_ESTIMATOR",
      itemScale = "mixed",
      methodExecution = build_cfa_execution(
        "mixed_item_scales_CFA",
        "not_run",
        interpretation_boundary = paste0(
          "当前基础 CFA 不会把有序题项静默连续化。请按同一测量模型使用单一题项尺度，",
          "或在支持混合 Pearson/polychoric 相关与相应估计器的专门规格中运行。"
        )
      )
    )
    adequacy <- assess_measurement_sample_adequacy(items, constructs, fitted)
    return(list(
      cfa = annotate_cfa_publication(adequacy$cfa, adequacy$passes),
      sampleAdequacy = adequacy$evidence,
      passes = FALSE,
      estimatedParameterCount = adequacy$estimatedParameterCount,
      casesPerParameter = adequacy$casesPerParameter,
      itemScale = item_scale
    ))
  }
  estimator <- if (identical(item_scale, "ordinal")) "WLSMV" else "MLR"
  ordered_items <- if (identical(item_scale, "ordinal")) names(items) else NULL
  fitted <- fit_cfa(items, constructs, estimator = estimator, ordered_items = ordered_items)
  fitted$itemScale <- item_scale
  adequacy <- assess_measurement_sample_adequacy(items, constructs, fitted)
  list(
    cfa = annotate_cfa_publication(adequacy$cfa, adequacy$passes),
    sampleAdequacy = adequacy$evidence,
    passes = adequacy$passes,
    estimatedParameterCount = adequacy$estimatedParameterCount,
    casesPerParameter = adequacy$casesPerParameter,
    itemScale = item_scale
  )
}

fit_cfa <- function(items, constructs, estimator = "ML", ordered_items = NULL) {
  if (nrow(items) < 20 || ncol(items) < 4) return(list(available = FALSE, reason = "CFA 需要至少 20 个完整案例和 4 个可变异题项"))

  requested_method <- paste0(
    "lavaan_", estimator,
    if (!is.null(ordered_items) && length(ordered_items)) "_ordered" else "_continuous",
    "_simple_structure_CFA"
  )
  lavaan_res <- tryCatch(
    fit_lavaan_cfa(items, constructs, estimator = estimator, ordered_items = ordered_items),
    error = function(error) list(available = FALSE, reason = conditionMessage(error))
  )
  if (!is.null(lavaan_res) && isTRUE(lavaan_res$available)) {
    lavaan_res$methodExecution <- build_cfa_execution(
      requested_method,
      paste0("lavaan_", estimator, "_simple_structure_CFA"),
      interpretation_boundary = "CFA 拟合与载荷必须结合估计器、题项尺度、收敛、异常解和样本量解释。"
    )
    return(lavaan_res)
  }

  lavaan_reason <- if (is.null(lavaan_res$reason)) {
    "lavaan CFA did not return an available result"
  } else {
    lavaan_res$reason
  }
  if (!is.null(ordered_items) && length(ordered_items) > 0L || identical(estimator, "WLSMV")) {
    lavaan_res$methodExecution <- build_cfa_execution(
      requested_method,
      "unavailable",
      fallback_reason = lavaan_reason,
      interpretation_boundary = "有序题项 WLSMV 失败时禁止回退到连续变量 ML CFA。"
    )
    return(lavaan_res)
  }

  construct_for_item <- character(0)

  kept_constructs <- list()
  for (construct in constructs) {
    ids <- intersect(unlist(construct$itemIds), names(items))
    if (length(ids) >= 2) {
      kept_constructs[[length(kept_constructs) + 1]] <- construct
      construct_for_item <- c(construct_for_item, setNames(rep(length(kept_constructs), length(ids)), ids))
    }
  }
  ordered_ids <- names(construct_for_item)
  if (length(ordered_ids) < 4 || length(kept_constructs) < 1) return(list(available = FALSE, reason = "CFA 简单结构中可用题项或构念不足"))
  researchpath_budget_custom_cfa(length(ordered_ids), length(kept_constructs))
  standardized <- scale(items[, ordered_ids, drop = FALSE])
  standardized <- standardized[complete.cases(standardized), , drop = FALSE]
  sample_correlation <- cor(standardized)
  sample_determinant <- determinant(sample_correlation, logarithm = TRUE)
  if (sample_determinant$sign <= 0) return(list(available = FALSE, reason = "CFA 样本相关矩阵非正定，不能进行无正则化 ML 估计"))
  p <- ncol(standardized); k <- length(kept_constructs); pair_count <- k * (k - 1) / 2
  build_model <- function(parameters) {
    loadings <- parameters[seq_len(p)]
    uniqueness <- exp(parameters[p + seq_len(p)])
    lower <- diag(1, k)
    if (pair_count > 0) lower[lower.tri(lower)] <- parameters[2 * p + seq_len(pair_count)]
    phi_raw <- lower %*% t(lower)
    phi <- cov2cor(phi_raw)
    lambda <- matrix(0, p, k)
    lambda[cbind(seq_len(p), as.integer(construct_for_item[ordered_ids]))] <- loadings
    sigma <- lambda %*% phi %*% t(lambda) + diag(uniqueness, p)
    list(sigma = sigma, lambda = lambda, phi = phi, uniqueness = uniqueness)
  }
  logdet_sample <- as.numeric(determinant(sample_correlation, logarithm = TRUE)$modulus)
  objective <- function(parameters) {
    model <- build_model(parameters)
    determinant_model <- determinant(model$sigma, logarithm = TRUE)
    if (determinant_model$sign <= 0) return(1e10)
    inverse <- tryCatch(solve(model$sigma), error = function(error) NULL)
    if (is.null(inverse)) return(1e10)
    as.numeric(determinant_model$modulus) + sum(diag(sample_correlation %*% inverse)) - logdet_sample - p
  }
  initial <- c(rep(0.7, p), rep(log(0.51), p), rep(0, pair_count))
  fit <- tryCatch(
    optim(initial, objective, method = "BFGS", control = list(maxit = 2000, reltol = 1e-10)),
    error = function(error) list(error = conditionMessage(error))
  )
  if (!is.null(fit$error)) return(list(available = FALSE, reason = paste("CFA 优化失败:", fit$error)))
  model <- build_model(fit$par)
  standardized_loadings <- numeric(p)
  for (index in seq_len(p)) {
    factor_index <- as.integer(construct_for_item[ordered_ids[index]])
    standardized_loadings[index] <- model$lambda[index, factor_index] / sqrt(model$sigma[index, index])
  }
  # Factor signs are arbitrary. Orient each factor consistently while retaining
  # within-factor sign reversals that may reveal miscoding or misspecification.
  for (factor_index in seq_len(k)) {
    indicator_indices <- which(as.integer(construct_for_item[ordered_ids]) == factor_index)
    if (sum(standardized_loadings[indicator_indices]) < 0) {
      standardized_loadings[indicator_indices] <- -standardized_loadings[indicator_indices]
      model$lambda[, factor_index] <- -model$lambda[, factor_index]
      model$phi[factor_index, ] <- -model$phi[factor_index, ]
      model$phi[, factor_index] <- -model$phi[, factor_index]
      model$phi[factor_index, factor_index] <- 1
    }
  }
  n <- nrow(standardized); parameter_count <- 2 * p + pair_count
  degrees_freedom <- as.integer(p * (p + 1) / 2 - parameter_count)
  chi_square <- n * fit$value
  baseline_chi <- n * (-logdet_sample)
  baseline_df <- p * (p - 1) / 2
  cfi_num <- max(chi_square - degrees_freedom, 0)
  cfi_den <- max(baseline_chi - baseline_df, 0)
  cfi <- if (cfi_den > 0) 1 - cfi_num / cfi_den else NA_real_
  if (is.finite(cfi) && cfi > 1.0) cfi <- 1.0
  if (is.finite(cfi) && cfi < 0.0) cfi <- 0.0
  tli <- if (degrees_freedom > 0) (baseline_chi / baseline_df - chi_square / degrees_freedom) / (baseline_chi / baseline_df - 1) else NA_real_
  rmsea <- if (degrees_freedom > 0) sqrt(max((chi_square - degrees_freedom) / (degrees_freedom * n), 0)) else NA_real_
  calc_rmsea_ci <- function(chi_val, df_val, sample_n, conf_level = 0.90) {
    if (df_val <= 0 || sample_n <= 1) return(list(lower = NA_real_, upper = NA_real_))
    tail <- (1 - conf_level) / 2
    find_ncp <- function(q, df, target_cdf) {
      objective <- function(ncp) pchisq(q, df = df, ncp = ncp) - target_cdf
      # The noncentral chi-square CDF decreases as the NCP increases. If the
      # target is already above the central CDF, the confidence bound is zero.
      if (objective(0) <= 0) return(0)
      upper <- max(q * 2, 10)
      while (objective(upper) > 0 && upper < 1e7) upper <- upper * 2
      if (objective(upper) > 0) return(NA_real_)
      uniroot(objective, c(0, upper))$root
    }
    ncp_lower <- tryCatch(find_ncp(chi_val, df_val, 1 - tail), error = function(e) NA_real_)
    ncp_upper <- tryCatch(find_ncp(chi_val, df_val, tail), error = function(e) NA_real_)
    list(lower = sqrt(ncp_lower / (df_val * sample_n)), upper = sqrt(ncp_upper / (df_val * sample_n)))
  }
  rmsea_ci <- calc_rmsea_ci(chi_square, degrees_freedom, n)
  observed_residual <- sample_correlation - cov2cor(model$sigma)
  srmr <- sqrt(mean(observed_residual[lower.tri(observed_residual, diag = TRUE)]^2))
  result <- list(
    available = TRUE, converged = fit$convergence == 0, iterations = fit$counts[[1]],
    completeCases = n, itemCount = p, factorCount = k,
    estimatedParameterCount = as.integer(parameter_count),
    chiSquare = finite_number(chi_square), degreesOfFreedom = degrees_freedom,
    pValue = if (degrees_freedom > 0) finite_number(pchisq(chi_square, degrees_freedom, lower.tail = FALSE)) else NA_real_,
    cfi = finite_number(cfi), tli = finite_number(tli), rmsea = finite_number(rmsea), srmr = finite_number(srmr),
    rmseaCiLower = finite_number(rmsea_ci$lower), rmseaCiUpper = finite_number(rmsea_ci$upper),
    estimator = "custom normal-theory maximum-likelihood simple-structure CFA (N-scaled FML)",
    itemIds = as.list(ordered_ids), standardizedLoadings = as.list(as.numeric(standardized_loadings)),
    factorCorrelations = lapply(seq_len(k), function(index) as.list(as.numeric(model$phi[index, ]))),
    constructIds = lapply(kept_constructs, function(construct) construct$id)
  )
  result$methodExecution <- build_cfa_execution(
    requested_method,
    "custom_normal_theory_ML_simple_structure_CFA",
    fallback_applied = TRUE,
    fallback_code = "CFA_LAVAAN_TO_CUSTOM_ML",
    fallback_reason = lavaan_reason,
    affected_outputs = as.list(c(
      "fitIndices",
      "standardizedLoadings",
      "factorCorrelations"
    )),
    interpretation_boundary = paste0(
      "lavaan 请求未成功，结果来自自研正态理论 ML 简单结构拟合器；",
      "不得视为与原请求估计器完全等价，需在正式研究中复核。"
    )
  )
  result
}

fit_lavaan_cfa <- function(items, constructs, estimator = "ML", ordered_items = NULL) {
  if (!requireNamespace("lavaan", quietly = TRUE)) {
    return(list(available = FALSE, reason = "lavaan package is not installed"))
  }

  lines <- character(0)
  kept_constructs <- list()
  construct_for_item <- character(0)

  for (construct in constructs) {
    ids <- intersect(unlist(construct$itemIds), names(items))
    if (length(ids) >= 2) {
      kept_constructs[[length(kept_constructs) + 1]] <- construct
      factor_name <- paste0("F_", construct$id)
      lines <- c(lines, paste0(factor_name, " =~ ", paste(ids, collapse = " + ")))
      construct_for_item <- c(construct_for_item, setNames(rep(length(kept_constructs), length(ids)), ids))
    }
  }

  if (length(lines) == 0 || length(kept_constructs) == 0) {
    return(list(available = FALSE, reason = "lavaan CFA 无法满足最少构念与题项结构"))
  }

  model_syntax <- paste(lines, collapse = "\n")

  fit <- tryCatch({
    if (!is.null(ordered_items) && length(ordered_items) > 0) {
      lavaan::cfa(model_syntax, data = items, estimator = if (estimator == "ML") "WLSMV" else estimator, ordered = ordered_items)
    } else {
      lavaan::cfa(model_syntax, data = items, estimator = estimator)
    }
  }, error = function(e) NULL)

  if (is.null(fit) || !isTRUE(lavaan::lavInspect(fit, "converged"))) {
    return(list(available = FALSE, reason = "lavaan CFA 模型估计未收敛"))
  }

  measures <- tryCatch(lavaan::fitMeasures(fit), error = function(e) NULL)
  if (is.null(measures)) return(list(available = FALSE, reason = "无法计算 lavaan 拟合指标"))

  # --- Standardized solution ---
  std_sol <- tryCatch(lavaan::standardizedSolution(fit), error = function(e) NULL)
  if (is.null(std_sol)) return(list(available = FALSE, reason = "无法计算 lavaan 标准化解"))

  # --- Unstandardized solution ---
  parameter_estimates_error <- NULL
  param_est <- tryCatch(
    lavaan::parameterEstimates(fit, ci = TRUE),
    error = function(e) {
      parameter_estimates_error <<- conditionMessage(e)
      NULL
    }
  )

  loadings_df <- std_sol[which(std_sol$op == "=~"), ]
  ordered_ids <- names(construct_for_item)
  std_loadings <- numeric(length(ordered_ids))
  unstd_loadings <- list()

  for (i in seq_along(ordered_ids)) {
    id <- ordered_ids[i]
    match_row <- loadings_df[which(loadings_df$rhs == id), ]
    if (nrow(match_row) > 0) {
      std_loadings[i] <- match_row$est.std[[1]]
    }
    # Unstandardized parameters
    if (!is.null(param_est)) {
      unstd_row <- param_est[which(param_est$op == "=~" & param_est$rhs == id), ]
      if (nrow(unstd_row) > 0) {
        unstd_loadings[[length(unstd_loadings) + 1]] <- list(
          itemId = id,
          estimate = finite_number(unstd_row$est[[1]]),
          se = finite_number(unstd_row$se[[1]]),
          z = finite_number(unstd_row$z[[1]]),
          pValue = finite_number(unstd_row$pvalue[[1]]),
          ciLower = finite_number(unstd_row$ci.lower[[1]]),
          ciUpper = finite_number(unstd_row$ci.upper[[1]])
        )
      }
    }
  }

  # --- Factor correlations ---
  k <- length(kept_constructs)
  phi <- diag(1.0, k)
  cov_df <- std_sol[which(std_sol$op == "~~" & std_sol$lhs != std_sol$rhs), ]
  factor_names <- paste0("F_", vapply(kept_constructs, function(c) c$id, character(1)))
  for (i in seq_len(k)) {
    for (j in seq_len(k)) {
      if (i != j) {
        f1 <- factor_names[i]
        f2 <- factor_names[j]
        m <- cov_df[which((cov_df$lhs == f1 & cov_df$rhs == f2) | (cov_df$lhs == f2 & cov_df$rhs == f1)), ]
        if (nrow(m) > 0) {
          phi[i, j] <- m$est.std[[1]]
        }
      }
    }
  }

  # --- Heywood case detection ---
  residual_df <- std_sol[which(std_sol$op == "~~" & std_sol$lhs == std_sol$rhs & std_sol$lhs %in% ordered_ids), ]
  heywood <- isTRUE(any(residual_df$est.std < 0, na.rm = TRUE)) ||
             isTRUE(any(abs(std_loadings) > 1.0, na.rm = TRUE))

  # --- Non-positive-definite check ---
  post_check <- tryCatch(lavaan::lavInspect(fit, "post.check"), error = function(e) NA)
  positive_definiteness <- cfa_positive_definiteness(post_check)
  not_positive_definite <- identical(positive_definiteness, "not_positive_definite")

  # --- Per-item R² ---
  r_squared <- tryCatch({
    rsq <- lavaan::lavInspect(fit, "rsquare")
    as.list(as.numeric(rsq[ordered_ids]))
  }, error = function(e) as.list(rep(NA_real_, length(ordered_ids))))

  # --- Residual correlation matrix ---
  residual_cor <- tryCatch({
    res <- lavaan::lavResiduals(fit, type = "cor.bollen")
    if (!is.null(res$cov.ov)) {
      mat <- as.matrix(res$cov.ov)
      mat_to_list(mat[ordered_ids, ordered_ids, drop = FALSE])
    } else NULL
  }, error = function(e) NULL)

  # --- Thresholds (for ordered/WLSMV) ---
  thresholds <- NULL
  if (!is.null(ordered_items) && length(ordered_items) > 0 && !is.null(param_est)) {
    thr_rows <- param_est[which(param_est$op == "|"), ]
    if (nrow(thr_rows) > 0) {
      thresholds <- lapply(seq_len(nrow(thr_rows)), function(r) {
        list(
          item = thr_rows$lhs[[r]],
          threshold = thr_rows$rhs[[r]],
          estimate = finite_number(thr_rows$est[[r]]),
          se = finite_number(thr_rows$se[[r]])
        )
      })
    }
  }

  # --- Modification indices (diagnostic only) ---
  mod_indices <- tryCatch({
    mi <- lavaan::modindices(fit, minimum.value = 3.84, sort. = TRUE)
    if (nrow(mi) > 0) {
      mi <- mi[seq_len(min(nrow(mi), 20)), ]  # Top 20
      lapply(seq_len(nrow(mi)), function(r) {
        list(
          lhs = mi$lhs[[r]],
          op = mi$op[[r]],
          rhs = mi$rhs[[r]],
          mi = finite_number(mi$mi[[r]]),
          epc = finite_number(mi$epc[[r]]),
          diagnosticOnly = TRUE
        )
      })
    } else list()
  }, error = function(e) list())

  # --- Fit measures ---
  get_m <- function(name, alt_name = NULL) {
    if (!is.null(measures[name]) && is.finite(measures[name])) return(as.numeric(measures[name]))
    if (!is.null(alt_name) && !is.null(measures[alt_name]) && is.finite(measures[alt_name])) return(as.numeric(measures[alt_name]))
    NA_real_
  }

  chisq <- get_m("chisq")
  chisq_scaled <- get_m("chisq.scaled")
  df_val <- get_m("df")
  p_val <- get_m("pvalue")
  p_val_scaled <- get_m("pvalue.scaled")
  cfi_val <- get_m("cfi")
  cfi_robust <- get_m("cfi.robust", "cfi.scaled")
  tli_val <- get_m("tli")
  tli_robust <- get_m("tli.robust", "tli.scaled")
  rmsea_val <- get_m("rmsea")
  rmsea_robust <- get_m("rmsea.robust", "rmsea.scaled")
  rmsea_ci_lower <- get_m("rmsea.ci.lower")
  rmsea_ci_upper <- get_m("rmsea.ci.upper")
  rmsea_ci_lower_robust <- get_m("rmsea.ci.lower.robust", "rmsea.ci.lower.scaled")
  rmsea_ci_upper_robust <- get_m("rmsea.ci.upper.robust", "rmsea.ci.upper.scaled")
  srmr_val <- get_m("srmr")

  result <- list(
    available = TRUE,
    converged = TRUE,
    diagnosticCodes = list(),
    parameterEstimatesAvailable = !is.null(param_est),
    parameterEstimatesError = parameter_estimates_error,
    positiveDefiniteness = positive_definiteness,
    iterations = as.integer(lavaan::lavInspect(fit, "iterations")),
    completeCases = as.integer(lavaan::nobs(fit)),
    itemCount = length(ordered_ids),
    factorCount = k,
    estimatedParameterCount = as.integer(lavaan::lavInspect(fit, "npar")),
    # Standard fit indices
    chiSquare = finite_number(chisq),
    chiSquareScaled = finite_number(chisq_scaled),
    degreesOfFreedom = as.integer(df_val),
    pValue = finite_number(p_val),
    pValueScaled = finite_number(p_val_scaled),
    cfi = finite_number(cfi_val),
    cfiRobust = finite_number(cfi_robust),
    tli = finite_number(tli_val),
    tliRobust = finite_number(tli_robust),
    rmsea = finite_number(rmsea_val),
    rmseaRobust = finite_number(rmsea_robust),
    srmr = finite_number(srmr_val),
    rmseaCiLower = finite_number(rmsea_ci_lower),
    rmseaCiUpper = finite_number(rmsea_ci_upper),
    rmseaCiLowerRobust = finite_number(rmsea_ci_lower_robust),
    rmseaCiUpperRobust = finite_number(rmsea_ci_upper_robust),
    # Solution
    estimator = paste0("lavaan formal measurement runner (", estimator, ")"),
    itemIds = as.list(ordered_ids),
    standardizedLoadings = as.list(as.numeric(std_loadings)),
    unstandardizedLoadings = unstd_loadings,
    factorCorrelations = lapply(seq_len(k), function(idx) as.list(as.numeric(phi[idx, ]))),
    constructIds = lapply(kept_constructs, function(construct) construct$id),
    rSquared = r_squared,
    # Diagnostics
    hasHeywoodCase = heywood,
    notPositiveDefinite = not_positive_definite,
    residualCorrelation = residual_cor,
    thresholds = thresholds,
    modificationIndices = mod_indices
  )

  # Add stable error codes for problematic cases
  if (heywood) {
    result$diagnosticCodes <- c(result$diagnosticCodes, "HEYWOOD_CASE_DETECTED")
  }
  if (not_positive_definite) {
    result$diagnosticCodes <- c(result$diagnosticCodes, "NOT_POSITIVE_DEFINITE")
  }
  if (!isTRUE(result$parameterEstimatesAvailable)) {
    result$diagnosticCodes <- c(result$diagnosticCodes, "CFA_PARAMETER_ESTIMATES_UNAVAILABLE")
  }
  if (identical(positive_definiteness, "unknown")) {
    result$diagnosticCodes <- c(result$diagnosticCodes, "CFA_POSTERIOR_POSITIVE_DEFINITENESS_UNKNOWN")
  }

  result
}
