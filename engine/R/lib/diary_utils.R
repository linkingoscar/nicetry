# Shared utility functions for diary and longitudinal engines
# Extracts finite scalars, handles data validation, and formats model results

#' Ensure a value is a finite numeric scalar
ensure_finite <- function(value) {
  numeric <- suppressWarnings(as.numeric(value))
  if (length(numeric) == 0L || !is.finite(numeric[[1]])) return(NULL)
  unname(numeric[[1]])
}

#' Standardized result scenario formatting
ensure_result_scenario <- function(scenario, result) {
  list(
    scenario = scenario,
    analysisType = result$analysisType,
    modelLabel = result$modelLabel,
    sampleSize = result$sampleSize,
    personCount = result$personCount,
    temporalEffect = result$temporalEffect,
    residualStructure = result$residualStructure,
    randomSlope = result$randomSlope,
    validForInterpretation = result$validForInterpretation,
    fixedEffects = result$fixedEffects,
    indirectEffects = result$indirectEffects
  )
}

#' Unified data validation for diary/panel models
validate_diary_data <- function(data, spec) {
  selected <- unique(c(
    spec$subjectVariableId,
    spec$timeVariableId,
    spec$outcomeVariableId,
    spec$predictorVariableId,
    spec$mediatorVariableId,
    spec$level2ModeratorVariableId,
    spec$crossClassVariableId,
    spec$exposureVariableId,
    unlist(spec$level2CovariateIds),
    unlist(spec$controlVariableIds)
  ))
  selected <- selected[!is.na(selected) & nzchar(selected)]
  missing_columns <- setdiff(selected, names(data))
  if (length(missing_columns) > 0L) {
    stop(paste0("DIARY_COLUMNS_NOT_FOUND: ", paste(missing_columns, collapse = ", ")))
  }
  prepared <- data[, selected, drop = FALSE]
  if (!is.null(spec$timeVariableId)) prepared[[spec$timeVariableId]] <- suppressWarnings(as.numeric(prepared[[spec$timeVariableId]]))
  numeric_ids <- setdiff(selected, c(spec$subjectVariableId, spec$crossClassVariableId))
  for (id in numeric_ids) prepared[[id]] <- suppressWarnings(as.numeric(prepared[[id]]))
  prepared <- prepared[complete.cases(prepared), , drop = FALSE]
  if (nrow(prepared) < 10L) stop("DIARY_INSUFFICIENT_COMPLETE_OBSERVATIONS")
  counts <- table(prepared[[spec$subjectVariableId]])
  if (length(counts) < 5L) stop("DIARY_INSUFFICIENT_PERSON_COUNT")
  if (any(counts < 2L)) {
    prepared <- prepared[
      prepared[[spec$subjectVariableId]] %in% names(counts[counts >= 2L]),
      ,
      drop = FALSE
    ]
  }
  prepared <- prepared[
    order(prepared[[spec$subjectVariableId]], prepared[[spec$timeVariableId]]),
    ,
    drop = FALSE
  ]
  if (!is.null(spec$timeVariableId) && anyDuplicated(prepared[, c(spec$subjectVariableId, spec$timeVariableId)])) {
    stop("DIARY_DUPLICATE_PERSON_TIME")
  }
  prepared
}

#' Extract VarCorr from lme4/lmerTest fit into standardized list format
format_variance_components <- function(fit) {
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
      pairedTerm = if (is.na(variance$var2[[index]])) NULL else as.character(variance$var2[[index]]),
      variance = ensure_finite(variance$vcov[[index]]),
      standardDeviation = ensure_finite(variance$sdcor[[index]])
    )
  })
}

#' Extract fixed effect estimates, SEs, df, t-values, p-values, CIs
format_lmer_coefficients <- function(fit, confidence_level, label_for) {
  coefficients <- as.data.frame(coef(summary(fit)))
  coefficients$term <- rownames(coefficients)
  rownames(coefficients) <- NULL
  critical <- qt(
    1 - (1 - confidence_level) / 2,
    df = pmax(1, suppressWarnings(as.numeric(coefficients$df)))
  )
  lapply(seq_len(nrow(coefficients)), function(index) {
    list(
      term = coefficients$term[[index]],
      label = label_for(coefficients$term[[index]]),
      estimate = ensure_finite(coefficients$Estimate[[index]]),
      standardError = ensure_finite(coefficients$`Std. Error`[[index]]),
      degreesOfFreedom = ensure_finite(coefficients$df[[index]]),
      statistic = ensure_finite(coefficients$`t value`[[index]]),
      pValue = ensure_finite(coefficients$`Pr(>|t|)`[[index]]),
      lower = ensure_finite(coefficients$Estimate[[index]] - critical[[index]] * coefficients$`Std. Error`[[index]]),
      upper = ensure_finite(coefficients$Estimate[[index]] + critical[[index]] * coefficients$`Std. Error`[[index]])
    )
  })
}

#' Build random effects formula string
build_random_terms <- function(spec, random_predictor) {
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
