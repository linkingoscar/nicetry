# 独立加载（测试/复用）时引导 seed 工具；入口脚本已先行 source。
if (!exists("researchpath_seed", mode = "function", inherits = TRUE)) {
  if (file.exists(file.path("engine", "R", "lib", "seed_utils.R"))) {
    source(file.path("engine", "R", "lib", "seed_utils.R"))
  }
}

.this_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
if (is.null(.this_dir) || nchar(.this_dir) == 0) .this_dir <- "."
if (file.exists(file.path(.this_dir, "diary_utils.R"))) {
  source(file.path(.this_dir, "diary_utils.R"))
  source(file.path(.this_dir, "centering_utils.R"))
  source(file.path(.this_dir, "time_series_utils.R"))
}
diary_pool_fixed_effects <- function(results, confidence_level, label_for) {
  term_sets <- lapply(results, function(result) {
    vapply(result$fixedEffects, function(row) row$term, character(1))
  })
  terms <- Reduce(intersect, term_sets)
  m <- length(results)
  lapply(terms, function(term) {
    rows <- lapply(results, function(result) {
      Filter(function(row) identical(row$term, term), result$fixedEffects)[[1]]
    })
    estimates <- vapply(rows, function(row) row$estimate, numeric(1))
    within_variances <- vapply(rows, function(row) row$standardError^2, numeric(1))
    estimate <- mean(estimates)
    within <- mean(within_variances)
    between <- if (m > 1L) var(estimates) else 0
    total <- within + (1 + 1 / m) * between
    relative_increase <- if (within > 0) ((1 + 1 / m) * between) / within else 0
    degrees_freedom <- if (relative_increase > 0) {
      (m - 1) * (1 + 1 / relative_increase)^2
    } else {
      1e6
    }
    standard_error <- sqrt(total)
    statistic <- estimate / standard_error
    p_value <- 2 * pt(abs(statistic), df = degrees_freedom, lower.tail = FALSE)
    critical <- qt(1 - (1 - confidence_level) / 2, df = degrees_freedom)
    fraction_missing_information <- if (total > 0) {
      ((1 + 1 / m) * between) / total
    } else {
      0
    }
    list(
      term = term,
      label = label_for(term),
      estimate = ensure_finite(estimate),
      standardError = ensure_finite(standard_error),
      degreesOfFreedom = ensure_finite(degrees_freedom),
      statistic = ensure_finite(statistic),
      pValue = ensure_finite(p_value),
      lower = ensure_finite(estimate - critical * standard_error),
      upper = ensure_finite(estimate + critical * standard_error),
      fractionMissingInformation = ensure_finite(fraction_missing_information)
    )
  })
}

diary_imputation_specification <- function(data, spec) {
  subject <- spec$subjectVariableId
  level1 <- unique(c(
    spec$timeVariableId,
    spec$outcomeVariableId,
    spec$predictorVariableId,
    unlist(spec$controlVariableIds)
  ))
  level2 <- unique(c(
    unlist(spec$level2CovariateIds),
    spec$level2ModeratorVariableId
  ))
  selected <- unique(c(subject, level1, level2))
  selected <- selected[!is.na(selected) & nzchar(selected)]
  imputation_data <- data[, selected, drop = FALSE]
  original_subject <- imputation_data[[subject]]
  imputation_data[[subject]] <- as.integer(factor(original_subject))
  for (id in setdiff(selected, subject)) {
    imputation_data[[id]] <- suppressWarnings(as.numeric(imputation_data[[id]]))
  }
  if (anyNA(imputation_data[[subject]])) stop("DIARY_MI_REQUIRES_COMPLETE_SUBJECT_ID")
  initial <- mice::mice(imputation_data, maxit = 0, printFlag = FALSE)
  method <- initial$method
  predictor_matrix <- initial$predictorMatrix
  method[] <- ""
  for (target in setdiff(selected, subject)) {
    if (!anyNA(imputation_data[[target]])) next
    method[[target]] <- if (target %in% level2) "2lonly.pmm" else "2l.pan"
    predictor_matrix[target, ] <- 0
    predictor_matrix[target, subject] <- -2
    fixed_predictors <- setdiff(selected, c(subject, target))
    predictor_matrix[target, fixed_predictors] <- 1
  }
  list(
    data = imputation_data,
    method = method,
    predictorMatrix = predictor_matrix,
    selected = selected,
    level1 = level1,
    level2 = level2
  )
}

fit_diary_lmm_mi <- function(data, spec, label_for, confidence_level) {
  suppressPackageStartupMessages(library(mice))
  setup <- diary_imputation_specification(data, spec)
  missing_counts <- vapply(setup$data, function(column) sum(is.na(column)), integer(1))
  if (sum(missing_counts) == 0L) {
    result <- fit_diary_lmm(validate_diary_data(data, spec), spec, label_for, confidence_level)
    result$missingData <- list(
      strategy = "multilevel_mi",
      imputationCount = 0L,
      message = "所选模型变量没有缺失值，因此未生成插补数据集。"
    )
    return(result)
  }
  random_seed <- if (is.null(spec$randomSeed)) 20260714L else researchpath_seed(spec$randomSeed)
  set.seed(random_seed)
  imputed <- mice::mice(
    setup$data,
    m = as.integer(spec$imputationCount),
    maxit = as.integer(spec$imputationIterations),
    method = setup$method,
    predictorMatrix = setup$predictorMatrix,
    seed = random_seed,
    printFlag = FALSE
  )
  completed_results <- lapply(seq_len(spec$imputationCount), function(index) {
    completed <- mice::complete(imputed, index)
    fit_diary_lmm(validate_diary_data(completed, spec), spec, label_for, confidence_level)
  })
  result <- completed_results[[1]]
  result$fixedEffects <- diary_pool_fixed_effects(
    completed_results,
    confidence_level,
    label_for
  )
  result$modelLabel <- paste0(result$modelLabel, "（二层多重插补合并）")
  result$missingData <- list(
    strategy = "multilevel_mi",
    imputationCount = as.integer(spec$imputationCount),
    iterations = as.integer(spec$imputationIterations),
    seed = random_seed,
    missingCounts = lapply(names(missing_counts), function(id) {
      list(variableId = id, missing = as.integer(missing_counts[[id]]))
    }),
    loggedEventCount = if (is.null(imputed$loggedEvents)) 0L else nrow(imputed$loggedEvents),
    pooling = "Rubin rules with Barnard-Rubin large-sample degrees of freedom"
  )
  result$provenance$missingDataEngine <- paste0(
    "mice ",
    as.character(packageVersion("mice")),
    " with 2l.pan/2lonly.pmm"
  )
  result
}
