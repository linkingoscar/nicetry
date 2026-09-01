run_imputation <- function() {
  suppressPackageStartupMessages(library(mice))
  data <- read_analysis_data()
  variables <- vapply(spec$variables, `[[`, character(1), "variableId")
  predictors <- unique(unlist(lapply(spec$variables, function(variable) unlist(variable$predictorIds))))
  pooled_ids <- if (!is.null(spec$pooledAnalysis)) unique(c(spec$pooledAnalysis$outcomeId, unlist(spec$pooledAnalysis$predictorIds, use.names = FALSE))) else character(0)
  passive_targets <- if (length(spec$passiveRules)) vapply(spec$passiveRules, `[[`, character(1), "targetVariableId") else character(0)
  selected <- unique(c(variables, predictors, passive_targets, pooled_ids, spec$clusterVariableId))
  selected <- selected[!is.na(selected) & nzchar(selected)]
  frame <- data[, selected, drop = FALSE]
  methods <- rep("", ncol(frame)); names(methods) <- names(frame)
  mapping <- c(pmm = "pmm", normal = "norm", logistic = "logreg", multinomial_logistic = "polyreg", ordinal_logistic = "polr", cart = "cart", two_level_normal = "2l.norm", two_level_binary = "2l.bin")
  infer_method <- function(values) {
    observed <- values[!is.na(values)]
    if (length(observed) == 0L) return("pmm")
    if (is.ordered(values)) return("polr")
    if (is.factor(values) || is.character(values)) {
      return(if (length(unique(observed)) <= 2L) "logreg" else "polyreg")
    }
    if (length(unique(observed)) <= 2L) return("logreg")
    if (is.numeric(values) && all(abs(observed - round(observed)) < 1e-8) && length(unique(observed)) >= 3L && length(unique(observed)) <= 7L) return("polr")
    "pmm"
  }
  predictor_matrix <- matrix(0, nrow = ncol(frame), ncol = ncol(frame), dimnames = list(names(frame), names(frame)))
  for (variable in spec$variables) {
    methods[[variable$variableId]] <- if (identical(variable$method, "auto")) infer_method(frame[[variable$variableId]]) else unname(mapping[[variable$method]])
    ids <- intersect(unlist(variable$predictorIds), names(frame))
    predictor_matrix[variable$variableId, ids] <- 1
    if (startsWith(variable$method, "two_level_") && !is.null(spec$clusterVariableId)) predictor_matrix[variable$variableId, spec$clusterVariableId] <- -2
  }
  if (length(spec$passiveRules)) {
    for (rule in spec$passiveRules) {
      match <- regexec("^([A-Za-z][A-Za-z0-9_-]*)[[:space:]]*\\*[[:space:]]*([A-Za-z][A-Za-z0-9_-]*)$", rule$expression)
      parts <- regmatches(rule$expression, match)[[1]]
      if (length(parts) != 3L) stop("MI_PASSIVE_EXPRESSION_NOT_SUPPORTED")
      if (!all(parts[2:3] %in% names(frame)) || !rule$targetVariableId %in% names(frame)) stop("MI_PASSIVE_COLUMN_NOT_FOUND")
      methods[[rule$targetVariableId]] <- paste0("~I(`", parts[[2]], "` * `", parts[[3]], "`)")
      predictor_matrix[rule$targetVariableId, parts[2:3]] <- 1
    }
  }
  original_missing <- colSums(is.na(frame))
  imputed <- mice::mice(frame, m = as.integer(spec$imputations), maxit = as.integer(spec$iterations), method = methods, predictorMatrix = predictor_matrix, seed = as.integer(spec$seed), printFlag = FALSE)
  artifacts <- vector("list", as.integer(spec$imputations))
  completed_datasets <- vector("list", as.integer(spec$imputations))
  for (index in seq_len(as.integer(spec$imputations))) {
    completed <- mice::complete(imputed, index)
    completed_datasets[[index]] <- completed
    path <- file.path(payload$artifactDirectory, sprintf("imputation-%03d.csv", index))
    write.csv(completed, path, row.names = FALSE, fileEncoding = "UTF-8")
    artifacts[[index]] <- list(imputation = index, temporary = basename(path))
  }
  convergence <- lapply(variables, function(variable) {
    chain <- imputed$chainMean[variable, , , drop = FALSE]
    list(variableId = variable, finalChainRange = finite(diff(range(chain[, ncol(chain), ], na.rm = TRUE))))
  })
  trace_diagnostics <- list()
  if ("trace" %in% unlist(spec$diagnostics, use.names = FALSE)) {
    for (variable in variables) {
      chain <- imputed$chainMean[variable, , , drop = FALSE]
      dimensions <- dim(chain)
      if (length(dimensions) != 3L) next
      for (iteration in seq_len(dimensions[[2]])) {
        trace_diagnostics[[length(trace_diagnostics) + 1L]] <- list(
          variableId = variable,
          iteration = as.integer(iteration),
          chainMeans = as.list(as.numeric(chain[1, iteration, ]))
        )
      }
    }
  }
  distribution_diagnostics <- list()
  if ("distribution" %in% unlist(spec$diagnostics, use.names = FALSE)) {
    distribution_diagnostics <- lapply(seq_along(variables), function(index) {
      variable <- variables[[index]]
      values <- unlist(lapply(completed_datasets, function(completed) completed[[variable]]), use.names = FALSE)
      numeric_values <- suppressWarnings(as.numeric(as.character(values)))
      numeric_values <- numeric_values[is.finite(numeric_values)]
      if (length(numeric_values) == 0L) {
        return(list(variableId = variable, available = FALSE, reason = "DISTRIBUTION_NUMERIC_SUMMARY_UNAVAILABLE"))
      }
      list(
        variableId = variable,
        available = TRUE,
        imputedMean = as.numeric(mean(numeric_values)),
        imputedSd = as.numeric(stats::sd(numeric_values)),
        imputedMinimum = as.numeric(min(numeric_values)),
        imputedMaximum = as.numeric(max(numeric_values))
      )
    })
  }
  missing_information <- lapply(variables, function(variable) list(variableId = variable, missingCount = as.integer(original_missing[[variable]]), missingRate = as.numeric(original_missing[[variable]] / nrow(frame))))
  pooled_estimates <- list()
  pooled_analysis <- NULL
  if (identical(spec$pooling, "rubin")) {
    if (is.null(spec$pooledAnalysis) || !identical(spec$pooledAnalysis$modelType, "linear_regression")) stop("MI_POOLED_MODEL_NOT_SUPPORTED")
    outcome_id <- spec$pooledAnalysis$outcomeId
    predictor_ids <- unlist(spec$pooledAnalysis$predictorIds, use.names = FALSE)
    analysis_ids <- unique(c(outcome_id, predictor_ids))
    if (!all(analysis_ids %in% names(frame))) stop("MI_POOLED_COLUMN_NOT_FOUND")
    formula <- stats::reformulate(predictor_ids, response = outcome_id, intercept = isTRUE(spec$pooledAnalysis$includeIntercept))
    fits <- lapply(completed_datasets, function(completed) {
      tryCatch(stats::lm(formula, data = completed), error = function(error) stop(paste0("MI_POOLED_MODEL_FAILED: ", conditionMessage(error))))
    })
    term_names <- names(stats::coef(fits[[1]]))
    if (length(term_names) == 0 || any(!vapply(fits, function(fit) all(term_names %in% names(stats::coef(fit))), logical(1)))) stop("MI_POOLED_RANK_DEFICIENT")
    pooled_estimates <- lapply(term_names, function(term) {
      q <- vapply(fits, function(fit) as.numeric(stats::coef(fit)[[term]]), numeric(1))
      u <- vapply(fits, function(fit) sqrt(stats::vcov(fit)[term, term]), numeric(1))
      pooled <- pool_rubin_estimates(q, u, vapply(fits, stats::df.residual, numeric(1)))
      list(
        term = term,
        estimate = pooled$pooledEstimate,
        standardError = pooled$pooledSE,
        degreesOfFreedom = pooled$degreesOfFreedom,
        statistic = pooled$tStatistic,
        pValue = pooled$pValue,
        confidenceLower = pooled$ciLower,
        confidenceUpper = pooled$ciUpper,
        withinVariance = pooled$withinVariance,
        betweenVariance = pooled$betweenVariance,
        totalVariance = pooled$totalVariance,
        RIV = pooled$RIV,
        FMI = pooled$FMI
      )
    })
    pooled_analysis <- list(model = spec$pooledAnalysis, m = as.integer(spec$imputations), method = "Rubin_Barnard_Rubin", estimates = pooled_estimates)
  }
  pooling_status <- if (identical(spec$pooling, "rubin")) "rubin" else "not_available"
  diagnostic_warnings <- list(message_entry("MI_MNAR_BOUNDARY", "warning", "Multiple imputation assumes MAR conditional on the declared predictor matrix; it does not resolve MNAR"))
  if ("overimputation" %in% unlist(spec$diagnostics, use.names = FALSE)) {
    diagnostic_warnings[[length(diagnostic_warnings) + 1L]] <- message_entry("MI_OVERIMPUTATION_NOT_AVAILABLE", "warning", "Overimputation diagnostics require a declared holdout protocol and are not silently approximated by completed-data summaries.")
  }
  if ("fraction_missing_information" %in% unlist(spec$diagnostics, use.names = FALSE) && !identical(spec$pooling, "rubin")) {
    diagnostic_warnings[[length(diagnostic_warnings) + 1L]] <- message_entry("MI_FMI_REQUIRES_RUBIN_POOLING", "warning", "Fraction of missing information is only defined for the declared pooled analysis.")
  }
  list(
    sampleFlow = list(original = nrow(frame), included = nrow(frame), excluded = 0L, missingMethod = "multiple imputation", imputations = as.integer(spec$imputations)),
    estimates = lapply(pooled_estimates, function(row) estimate_entry(row$term, row$term, row$estimate, row$standardError, row$statistic, row$degreesOfFreedom, row$pValue, row$confidenceLower, row$confidenceUpper, "pooled_model")),
    diagnostics = c(list(message_entry("MI_CHAINS_COMPLETED", "info", sprintf("Completed %s deterministic chains", spec$imputations))), if (length(trace_diagnostics)) list(message_entry("MI_TRACE_EMITTED", "info", sprintf("Emitted %s chain trace rows", length(trace_diagnostics)))) else list(), if (length(distribution_diagnostics)) list(message_entry("MI_DISTRIBUTION_EMITTED", "info", sprintf("Emitted %s distribution summaries", length(distribution_diagnostics)))) else list(), if (identical(spec$pooling, "rubin")) list(message_entry("MI_RUBIN_POOLED", "info", "下游线性回归已逐份拟合并按 Rubin/Barnard–Rubin 规则合并")) else list()),
    warnings = diagnostic_warnings,
    provenance = list(engine = "R mice", engineVersion = as.character(packageVersion("mice")), softwareVersions = package_versions(c("mice", if (identical(spec$pooling, "rubin")) "stats" else character(0))), estimand = if (identical(spec$pooling, "rubin")) "pooled linear regression coefficient" else "completed-data distribution", degreesOfFreedomMethod = if (identical(spec$pooling, "rubin")) "Barnard-Rubin" else "not applicable"),
    familyResult = list(family = family, imputations = as.integer(spec$imputations), convergence = convergence, missingInformation = missing_information, artifacts = artifacts, poolingStatus = pooling_status, pooledAnalysis = pooled_analysis, trace = trace_diagnostics, distribution = distribution_diagnostics, fractionMissingInformation = lapply(pooled_estimates, function(row) list(term = row$term, FMI = row$FMI, RIV = row$RIV)))
  )
}
