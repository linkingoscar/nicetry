# ---------------------------------------------------------------------------
# CFA-based construct validity: CR, AVE, Fornell-Larcker, HTMT
# ---------------------------------------------------------------------------

single_factor_eigen_loadings <- function(item_frame) {
  correlation <- cor(item_frame)
  decomposition <- eigen(correlation, symmetric = TRUE)
  loadings <- decomposition$vectors[, 1] * sqrt(max(decomposition$values[1], 0))
  if (sum(loadings) < 0) loadings <- -loadings
  names(loadings) <- names(item_frame)
  loadings
}

build_validity_method_execution <- function(construct_validity, cfa_result) {
  fallback_applied <- any(vapply(
    construct_validity,
    function(row) isTRUE(row$fallbackApplied),
    logical(1)
  ))
  list(
    requestedMethod = "CFA standardized loadings",
    executedMethod = if (fallback_applied) {
      "single-factor eigen approximation"
    } else {
      "CFA standardized loadings"
    },
    fallbackApplied = fallback_applied,
    fallbackCode = if (fallback_applied) {
      "CFA_UNAVAILABLE_FALLBACK_SINGLE_FACTOR_EIGEN"
    } else {
      NULL
    },
    fallbackReason = if (fallback_applied) {
      if (is.null(cfa_result$reason)) {
        "CFA 未返回可用于全部题项的标准化载荷"
      } else {
        cfa_result$reason
      }
    } else {
      NULL
    },
    affectedOutputs = if (fallback_applied) {
      as.list(c(
        "compositeReliability",
        "averageVarianceExtracted",
        "sqrtAve",
        "fornellLarckerDiagonal"
      ))
    } else {
      list()
    },
    interpretationBoundary = if (fallback_applied) {
      paste0(
        "CR、AVE 与 Fornell–Larcker 对角线来自单因子特征分解近似，",
        "不是 CFA 标准化解；仅供探索性诊断。"
      )
    } else {
      NULL
    }
  )
}

build_construct_validity <- function(constructs, item_frame, cfa_result) {
  loading_by_item <- list()
  if (isTRUE(cfa_result$available)) {
    for (index in seq_along(cfa_result$itemIds)) {
      loading_by_item[[cfa_result$itemIds[[index]]]] <- cfa_result$standardizedLoadings[[index]]
    }
  }
  lapply(constructs, function(construct) {
    ids <- intersect(unlist(construct$itemIds), names(item_frame))
    eigen_fallback <- single_factor_eigen_loadings(item_frame[, ids, drop = FALSE])
    used_eigen_fallback <- FALSE
    loadings <- vapply(ids, function(id) {
      cfa_loading <- loading_by_item[[id]]
      if (!is.null(cfa_loading) && length(cfa_loading) == 1L && isTRUE(is.finite(cfa_loading))) {
        return(cfa_loading)
      }
      used_eigen_fallback <<- TRUE
      eigen_fallback[[id]]
    }, numeric(1))
    loadings <- pmax(pmin(loadings, 0.999999), -0.999999)
    item_count <- length(ids)
    if (item_count >= 2L) {
      error_variance <- pmax(1 - loadings^2, 0)
      composite_reliability <- sum(loadings)^2 / (sum(loadings)^2 + sum(error_variance))
      ave <- mean(loadings^2)
      reliability_warning <- NULL
    } else {
      composite_reliability <- NA_real_
      ave <- NA_real_
      reliability_warning <- "单题项构念不计算 CR/AVE，Fornell-Larcker 标记为 not_evaluable"
    }
    ordinal_reliability <- tryCatch(
      calc_ordinal_reliability(item_frame, ids),
      error = function(error) list()
    )
    list(
      constructId = construct$id,
      label = construct$label,
      scoreId = construct$scoreId,
      alpha = if (is.null(construct$alpha)) NA_real_ else finite_number(construct$alpha),
      omega = if (is.null(construct$omega)) NA_real_ else finite_number(construct$omega),
      ordinalAlpha = finite_number(ordinal_reliability$ordinalAlpha),
      ordinalOmega = finite_number(ordinal_reliability$ordinalOmega),
      compositeReliability = finite_number(composite_reliability),
      averageVarianceExtracted = finite_number(ave),
      sqrtAve = finite_number(sqrt(ave)),
      standardizedLoadings = as.list(as.numeric(loadings)),
      itemIds = as.list(ids),
      itemCount = as.integer(item_count),
      reliabilityWarning = reliability_warning,
      loadingSource = if (used_eigen_fallback) "single-factor eigen fallback" else "CFA",
      fallbackApplied = used_eigen_fallback,
      discriminantValidityPass = FALSE
    )
  })
}

calc_cr_ave <- function(std_loadings_per_construct) {
  # std_loadings_per_construct: list of lists, each sublist contains
  # numeric standardized loadings for one construct
  lapply(std_loadings_per_construct, function(entry) {
    construct_id <- entry$constructId
    loadings <- as.numeric(unlist(entry$loadings))
    loadings <- loadings[is.finite(loadings)]
    k <- length(loadings)
    if (k < 2) {
      return(list(
        constructId = construct_id,
        compositeReliability = NA_real_,
        averageVarianceExtracted = NA_real_,
        sqrtAve = NA_real_,
        itemCount = k
      ))
    }
    loadings_clamped <- pmax(pmin(loadings, 0.999999), -0.999999)
    error_variance <- pmax(1 - loadings_clamped^2, 0)
    cr <- sum(loadings_clamped)^2 / (sum(loadings_clamped)^2 + sum(error_variance))
    ave <- mean(loadings_clamped^2)
    list(
      constructId = construct_id,
      compositeReliability = finite_number(cr),
      averageVarianceExtracted = finite_number(ave),
      sqrtAve = finite_number(sqrt(ave)),
      itemCount = as.integer(k)
    )
  })
}

calc_fornell_larcker <- function(cr_ave_results, factor_correlations) {
  k <- length(cr_ave_results)
  if (k < 2) return(list(available = FALSE, reason = "需要至少两个构念进行区分效度检验"))

  sqrt_aves <- vapply(cr_ave_results, function(r) {
    v <- r$sqrtAve
    if (is.null(v) || !is.finite(v)) NA_real_ else v
  }, numeric(1))

  phi <- if (is.matrix(factor_correlations)) {
    factor_correlations
  } else if (is.list(factor_correlations) && length(factor_correlations) > 0L) {
    do.call(rbind, lapply(factor_correlations, function(row) as.numeric(unlist(row))))
  } else {
    NULL
  }
  if (is.null(phi)) {
    return(list(
      available = FALSE,
      reason = "factor_correlations_unavailable；不得用单位矩阵替代 CFA 潜变量相关后宣称区分效度通过",
      matrix = mat_to_list(matrix(NA_real_, k, k)),
      constructEvaluations = lapply(cr_ave_results, function(entry) list(
        constructId = entry$constructId, status = "not_evaluable", pass = NA
      )),
      source = "unavailable"
    ))
  }

  # Build Fornell-Larcker matrix: diagonal = sqrt(AVE), off-diagonal = |factor correlation|
  fl_matrix <- matrix(NA_real_, k, k)
  for (i in seq_len(k)) {
    fl_matrix[i, i] <- sqrt_aves[i]
    if (i < k) {
      for (j in seq.int(i + 1L, k)) {
        fl_matrix[i, j] <- abs(phi[i, j])
        fl_matrix[j, i] <- abs(phi[j, i])
      }
    }
  }

  # Evaluate pass/fail per construct
  evaluations <- lapply(seq_len(k), function(i) {
    if (!is.finite(sqrt_aves[i])) {
      return(list(
        constructId = cr_ave_results[[i]]$constructId,
        status = "not_evaluable",
        pass = NA
      ))
    }
    other_cors <- abs(phi[i, -i])
    if (any(!is.finite(other_cors))) {
      return(list(
        constructId = cr_ave_results[[i]]$constructId,
        status = "not_evaluable",
        pass = NA
      ))
    }
    passes <- all(sqrt_aves[i] > other_cors)
    list(
      constructId = cr_ave_results[[i]]$constructId,
      status = if (passes) "pass" else "fail",
      pass = passes
    )
  })

  list(
    available = TRUE,
    matrix = mat_to_list(fl_matrix),
    constructEvaluations = evaluations,
    source = "CFA latent-factor correlations"
  )
}

calc_cfa_validity_bundle <- function(cfa_result, constructs, item_frame) {
  if (!isTRUE(cfa_result$available)) {
    return(list(available = FALSE, reason = "CFA 结果不可用"))
  }

  item_ids_flat <- unlist(cfa_result$itemIds)
  std_loadings <- as.numeric(unlist(cfa_result$standardizedLoadings))

  # Map loadings to constructs
  loadings_per_construct <- lapply(constructs, function(construct) {
    ids <- intersect(unlist(construct$itemIds), item_ids_flat)
    construct_loadings <- vapply(ids, function(id) {
      idx <- match(id, item_ids_flat)
      if (!is.na(idx)) std_loadings[idx] else NA_real_
    }, numeric(1))
    list(constructId = construct$id, loadings = construct_loadings, itemIds = ids)
  })

  cr_ave <- calc_cr_ave(loadings_per_construct)
  fornell <- calc_fornell_larcker(cr_ave, cfa_result$factorCorrelations)

  # HTMT (reuse existing function from validity.R)
  htmt_result <- if (length(constructs) >= 2 && ncol(item_frame) >= 2) {
    htmt_mat <- calc_htmt_matrix(item_frame, constructs)
    list(
      available = TRUE,
      matrix = mat_to_list(htmt_mat)
    )
  } else {
    list(available = FALSE, reason = "HTMT 需要至少两个构念")
  }

  list(
    available = TRUE,
    compositeReliabilityAndAve = cr_ave,
    fornellLarcker = fornell,
    htmt = htmt_result
  )
}
