args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Usage: run_advanced_analysis.R <input.json> <output.json>")

# R 4.6 UCRT can inherit an unavailable POSIX locale (for example C.UTF-8)
# from a Python or Node caller on Windows.  Switch the parser locale before
# loading UTF-8 R libraries so Chinese warnings and interpretation boundaries
# are not corrupted or rejected by `source(..., encoding = "UTF-8")`.
suppressWarnings(Sys.setlocale("LC_CTYPE", "English_United States.utf8"))
suppressPackageStartupMessages(library(jsonlite))

payload <- fromJSON(args[[1]], simplifyVector = FALSE)
spec <- payload$spec
family <- spec$family
args_all <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("--file=", args_all, value = TRUE)
script_dir <- if (length(file_arg) > 0) dirname(substring(file_arg[1], 8)) else "engine/R"
source(file.path(script_dir, "lib", "seed_utils.R"), local = environment())
source(file.path(script_dir, "lib", "output_contract.R"), local = environment())
set.seed(researchpath_seed(spec$seed))
progress_path <- if (is.null(payload$progressPath)) NULL else payload$progressPath
cancel_path <- if (is.null(payload$cancelPath)) NULL else payload$cancelPath
# All advanced families share the same progress/cancel contract. Loading
# runtime.R unconditionally removes the former no-op fallback for families
# that used to skip it (experimental_design/multilevel_model/longitudinal_model).
source(file.path(script_dir, "lib", "runtime.R"), local = environment())
# 部分 family 分支不加载 lib/runtime.R，此处本地提供一致的有限数规范化。
finite_number <- function(value) {
  if (is.null(value) || length(value) == 0 || is.na(value) || !is.finite(value)) return(NA_real_)
  as.numeric(value)
}
runner_environment <- environment()
source_r_library <- function(path) {
  source(path, local = runner_environment, encoding = "UTF-8")
}
if (identical(family, "questionnaire_measurement")) {
  source_r_library(file.path(script_dir, "lib", "runtime.R"))
  source_r_library(file.path(script_dir, "lib", "parallel.R"))
  source_r_library(file.path(script_dir, "lib", "resource_budget.R"))
  source_r_library(file.path(script_dir, "lib", "validity.R"))
  source_r_library(file.path(script_dir, "lib", "efa.R"))
  source_r_library(file.path(script_dir, "lib", "cfa.R"))
  source_r_library(file.path(script_dir, "lib", "cfa_validity.R"))
  source_r_library(file.path(script_dir, "lib", "invariance.R"))
  source_r_library(file.path(script_dir, "lib", "esem_bifactor.R"))
  source_r_library(file.path(script_dir, "lib", "cmb.R"))
  source_r_library(file.path(script_dir, "lib", "questionnaire_measurement_runner.R"))
}
if (identical(family, "multiple_imputation")) {
  source_r_library(file.path(script_dir, "lib", "runtime.R"))
  source_r_library(file.path(script_dir, "lib", "resource_budget.R"))
  source_r_library(file.path(script_dir, "lib", "mi_rubin.R"))
  source_r_library(file.path(script_dir, "lib", "imputation_runner.R"))
}
if (identical(family, "multilevel_model")) {
  source_r_library(file.path(script_dir, "lib", "aggregation_diagnostics.R"))
  source_r_library(file.path(script_dir, "lib", "multilevel_aggregation.R"))
  source_r_library(file.path(script_dir, "lib", "aggregation_runner.R"))
}
if (identical(family, "longitudinal_model")) {
  source_r_library(file.path(script_dir, "lib", "longitudinal_advanced.R"))
}
if (identical(family, "power_analysis")) {
  source_r_library(file.path(script_dir, "lib", "runtime.R"))
  source_r_library(file.path(script_dir, "lib", "resource_budget.R"))
  source_r_library(file.path(script_dir, "lib", "power_monte_carlo.R"))
  source_r_library(file.path(script_dir, "lib", "power_t_test.R"))
  source_r_library(file.path(script_dir, "lib", "power_analytic.R"))
}
if (identical(family, "experimental_design")) {
  source_r_library(file.path(script_dir, "lib", "experimental_cluster_glm.R"))
  source_r_library(file.path(script_dir, "lib", "experiment_posthoc.R"))
}

# 未加载 lib/runtime.R 的 family 需要本地等价实现，使 progressPath/cancelPath
# 传入后真正生效（进度回调与协作式取消），而不是静默空转。
if (!exists("write_progress", inherits = FALSE)) {
  write_progress <- function(...) invisible(NULL)
}
if (!exists("check_cancel", inherits = FALSE)) {
  check_cancel <- function() {
    if (!is.null(cancel_path) && file.exists(cancel_path)) stop("ANALYSIS_CANCELLED")
  }
}

rows <- function(value) {
  if (is.null(value) || NROW(value) == 0L) return(list())
  value <- as.data.frame(value)
  lapply(seq_len(nrow(value)), function(index) {
    result <- lapply(value, function(column) column[[index]])
    names(result) <- names(value)
    result
  })
}
finite <- function(value) {
  value <- as.numeric(value)
  if (length(value) == 0L || !is.finite(value[[1]])) return(NULL)
  value[[1]]
}
is_finite_scalar <- function(value) {
  length(value) == 1L && is.finite(as.numeric(value[[1]]))
}
message_entry <- function(code, severity, message) {
  list(code = code, severity = severity, message = message)
}
estimate_entry <- function(id, label, estimate, se = NULL, statistic = NULL, df = NULL, p = NULL, lower = NULL, upper = NULL, scale = "raw") {
  list(
    id = id, label = label, estimate = as.numeric(estimate),
    standardError = finite(se), statistic = finite(statistic),
    degreesOfFreedom = finite(df), pValue = finite(p),
    confidenceLower = finite(lower), confidenceUpper = finite(upper), scale = scale
  )
}
read_analysis_data <- function() {
  if (is.null(payload$dataPath)) stop("This analysis family requires a dataset")
  read.csv(payload$dataPath, check.names = FALSE, na.strings = c("", "NA"), fileEncoding = "UTF-8")
}

package_versions <- function(packages) {
  values <- vapply(packages, function(package) as.character(packageVersion(package)), character(1))
  as.list(values)
}


run_experimental <- function() {
  if (identical(spec$analysisType, "glm_cluster")) return(run_cluster_glm())
  suppressPackageStartupMessages(library(afex))
  suppressPackageStartupMessages(library(emmeans))
  data <- prepare_experimental_data(read_analysis_data())
  outcomes <- unlist(spec$outcomeIds)
  if (length(outcomes) != 1L) stop("Formal execution currently requires one outcome per experimental run")
  outcome <- outcomes[[1]]
  between <- if (length(spec$betweenFactors)) vapply(spec$betweenFactors, `[[`, character(1), "variableId") else character(0)
  within <- if (length(spec$withinFactors)) vapply(spec$withinFactors, `[[`, character(1), "id") else character(0)
  covariates <- unlist(spec$covariateIds)

  for (factor_spec in spec$betweenFactors) {
    name <- factor_spec$variableId
    data[[name]] <- factor(data[[name]])
    if (!is.null(factor_spec$referenceLevel)) {
      ref_level <- as.character(factor_spec$referenceLevel)
      if (ref_level %in% levels(data[[name]])) {
        data[[name]] <- relevel(data[[name]], ref = ref_level)
      }
    }
    if (identical(factor_spec$coding, "treatment")) {
      contrasts(data[[name]]) <- contr.treatment(levels(data[[name]]))
    } else if (identical(factor_spec$coding, "helmert")) {
      contrasts(data[[name]]) <- contr.helmert(levels(data[[name]]))
    } else {
      contrasts(data[[name]]) <- contr.sum(levels(data[[name]]))
    }
  }
  for (name in within) data[[name]] <- factor(data[[name]])
  factors <- c(between, within)
  data$.rp_subject <- if (is.null(spec$subjectId)) seq_len(nrow(data)) else data[[spec$subjectId]]
  selected <- unique(c(outcome, factors, covariates, ".rp_subject"))
  original_n <- nrow(data)
  if (length(within)) {
    subject_cells <- data[, c(".rp_subject", within), drop = FALSE]
    if (any(!complete.cases(subject_cells))) stop("EXPERIMENT_MISSING_SUBJECT_OR_WITHIN_LEVEL", call. = FALSE)
    if (any(duplicated(subject_cells))) stop("EXPERIMENT_DUPLICATE_SUBJECT_CELL", call. = FALSE)
    expected_cells <- prod(vapply(within, function(name) nlevels(data[[name]]), integer(1)))
    complete_by_subject <- tapply(complete.cases(data[, selected, drop = FALSE]), data$.rp_subject, sum)
    if (any(complete_by_subject != expected_cells)) stop("EXPERIMENT_INCOMPLETE_WITHIN_SUBJECT_CELLS", call. = FALSE)
  }
  data <- data[complete.cases(data[, selected, drop = FALSE]), , drop = FALSE]
  if (nrow(data) < 4L) stop("EXPERIMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS", call. = FALSE)

  if (length(factors) > 1L) {
    cell_counts <- do.call(table, c(unname(data[factors]), list(useNA = "no")))
    if (any(cell_counts == 0L)) stop("EXPERIMENT_EMPTY_CELL", call. = FALSE)
  }

  if (length(covariates) && identical(spec$covariateCentering, "grand_mean")) {
    for (cov in covariates) {
      data[[cov]] <- data[[cov]] - mean(data[[cov]], na.rm = TRUE)
    }
  }

  warnings <- list()
  diagnostics <- list(message_entry("EXPERIMENT_CELL_COUNTS", "info", "Cell counts and estimability were evaluated by afex before inference"))

  if (length(between) > 0L) {
    tryCatch({
      suppressPackageStartupMessages(library(car))
      form_levene <- as.formula(sprintf("%s ~ %s", outcome, paste(between, collapse = " * ")))
      levene <- car::leveneTest(form_levene, data = data)
      if (!is.na(levene$`Pr(>F)`[1]) && levene$`Pr(>F)`[1] < 0.05) {
        warnings[[length(warnings) + 1L]] <- message_entry("LEVENE_VIOLATION", "warning", "Levene's test indicates a violation of the homogeneity of variance assumption (p < .05).")
        diagnostics[[length(diagnostics) + 1L]] <- message_entry("LEVENE_DETAIL", "warning", sprintf("Levene's Test F = %.2f, p = %.3f", levene$`F value`[1], levene$`Pr(>F)`[1]))
      }
    }, error = function(e) {
      diagnostics[[length(diagnostics) + 1L]] <<- message_entry("LEVENE_TEST_ESTIMATION_FAILED", "info", sprintf("Levene's test failed to compute: %s", conditionMessage(e)))
    })
  }

  if (length(covariates) && length(between) && identical(spec$homogeneityOfSlopes, "check_and_warn")) {
    interaction_terms <- unlist(lapply(covariates, function(c) paste(c, between, sep="*")))
    check_formula <- as.formula(sprintf("%s ~ %s", outcome, paste(interaction_terms, collapse=" + ")))
    check_fit <- tryCatch(anova(lm(check_formula, data = data)), error = function(e) NULL)
    if (!is.null(check_fit)) {
       interaction_rows <- grep(":", rownames(check_fit))
       p_values <- check_fit$`Pr(>F)`[interaction_rows]
       if (any(!is.na(p_values) & p_values < 0.05)) {
          warnings[[length(warnings) + 1L]] <- message_entry("SLOPES_NOT_HOMOGENEOUS", "warning", "Significant interaction between covariates and between-subjects factors detected (p < .05). The assumption of homogeneity of regression slopes may be violated; interpret adjusted marginal means with caution.")
       }
    }
  }
  fixed <- if (length(factors)) paste(factors, collapse = " * ") else "1"
  if (length(covariates)) fixed <- paste(fixed, paste(covariates, collapse = " + "), sep = " + ")
  fixed_formula <- as.formula(sprintf("%s ~ %s", outcome, fixed))
  design_matrix <- model.matrix(fixed_formula, data = data)
  if (qr(design_matrix)$rank < ncol(design_matrix)) stop("EXPERIMENT_DESIGN_MATRIX_RANK_DEFICIENT", call. = FALSE)
  error_term <- if (length(within)) sprintf("Error(.rp_subject/(%s))", paste(within, collapse = " * ")) else "Error(.rp_subject)"
  formula <- as.formula(sprintf("%s ~ %s + %s", outcome, fixed, error_term))
  fit <- tryCatch(
    afex::aov_car(formula, data = data, type = if (identical(spec$sumOfSquares, "II")) 2L else 3L, factorize = FALSE, observed = covariates),
    error = function(error) stop(sprintf("EXPERIMENT_ESTIMATION_FAILED: %s", conditionMessage(error)), call. = FALSE)
  )
  correction_method <- NULL
  if (length(within)) {
    correction_method <- switch(spec$sphericityCorrection, greenhouse_geisser = "GG", huynh_feldt = "HF", "GG")
    table <- as.data.frame(anova(fit, correction = correction_method, es = "pes"))
  } else {
    table <- as.data.frame(anova(fit, es = "pes"))
  }
  table$term <- rownames(table)
  rownames(table) <- NULL
  find_column <- function(pattern) {
    matches <- grep(pattern, names(table), ignore.case = TRUE, value = TRUE)
    if (length(matches)) matches[[1]] else NULL
  }
  f_col <- find_column("^F$")
  p_col <- find_column("Pr\\(>F\\)")
  num_col <- find_column("num.*Df")
  den_col <- find_column("den.*Df")
  pes_col <- find_column("pes|partial")
  omnibus <- lapply(seq_len(nrow(table)), function(index) {
    list(
      term = table$term[[index]], numeratorDf = finite(if (!is.null(num_col)) table[[num_col]][[index]] else NULL),
      denominatorDf = finite(if (!is.null(den_col)) table[[den_col]][[index]] else NULL),
      f = finite(if (!is.null(f_col)) table[[f_col]][[index]] else NULL),
      pValue = finite(if (!is.null(p_col)) table[[p_col]][[index]] else NULL),
      partialEtaSquared = finite(if (!is.null(pes_col)) table[[pes_col]][[index]] else NULL)
    )
  })
  estimable_omnibus <- Filter(function(item) !is.null(item$partialEtaSquared), omnibus)
  estimates <- lapply(seq_along(estimable_omnibus), function(index) {
    item <- estimable_omnibus[[index]]
    estimate_entry(paste0("omnibus_", index), item$term, item$partialEtaSquared, statistic = item$f, df = item$denominatorDf, p = item$pValue, scale = "partial_eta_squared")
  })
  emm_rows <- list()
  contrast_rows <- list()
  planned_contrast_rows <- list()
  if (length(factors)) {
    grid <- emmeans::emmeans(fit, specs = factors)
    emm_rows <- rows(as.data.frame(confint(grid, level = as.numeric(spec$confidenceLevel))))
    if (identical(spec$postHocAdjustment, "games_howell")) {
      if (length(between) != 1L || length(within) != 0L || length(covariates) != 0L) {
        stop("GAMES_HOWELL_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES", call. = FALSE)
      }
      contrast_rows <- fit_games_howell(data, outcome, between[[1]], as.numeric(spec$confidenceLevel))
    } else {
      adjustment <- switch(spec$postHocAdjustment, benjamini_hochberg = "BH", spec$postHocAdjustment)
      contrast_rows <- rows(as.data.frame(summary(pairs(grid), infer = c(TRUE, TRUE), level = as.numeric(spec$confidenceLevel), adjust = adjustment)))
    }
    if (length(spec$plannedContrasts)) {
      if (length(between) != 1L || length(within) != 0L || length(covariates) != 0L) {
        stop("PLANNED_CONTRAST_REQUIRES_SINGLE_BETWEEN_FACTOR_NO_COVARIATES", call. = FALSE)
      }
      factor_name <- between[[1]]
      factor_levels <- levels(data[[factor_name]])
      planned_methods <- list()
      planned_families <- list()
      for (planned in spec$plannedContrasts) {
        if (is.null(names(planned$weights))) stop("PLANNED_CONTRAST_WEIGHTS_MUST_BE_NAMED", call. = FALSE)
        unknown_levels <- setdiff(names(planned$weights), factor_levels)
        if (length(unknown_levels)) stop("PLANNED_CONTRAST_LEVEL_NOT_FOUND", call. = FALSE)
        weights <- setNames(rep(0, length(factor_levels)), factor_levels)
        weights[names(planned$weights)] <- vapply(planned$weights, as.numeric, numeric(1))
        if (sum(abs(weights) > 1e-12) < 2L || abs(sum(weights)) > 1e-8) {
          stop("PLANNED_CONTRAST_WEIGHTS_INVALID", call. = FALSE)
        }
        planned_methods[[planned$id]] <- weights
        planned_families[[planned$id]] <- planned$multiplicityFamilyId
      }
      adjustment <- switch(spec$postHocAdjustment, benjamini_hochberg = "BH", spec$postHocAdjustment)
      if (!adjustment %in% c("holm", "BH")) {
        stop("PLANNED_CONTRAST_ADJUSTMENT_NOT_SUPPORTED", call. = FALSE)
      }
      planned_grid <- emmeans::emmeans(fit, specs = factor_name)
      family_ids <- unique(unlist(planned_families, use.names = FALSE))
      family_summaries <- lapply(family_ids, function(family_id) {
        method_ids <- names(planned_methods)[vapply(
          names(planned_methods),
          function(id) identical(planned_families[[id]], family_id),
          logical(1)
        )]
        family_methods <- planned_methods[method_ids]
        family_summary <- as.data.frame(summary(
          emmeans::contrast(planned_grid, method = family_methods),
          infer = c(TRUE, TRUE),
          level = as.numeric(spec$confidenceLevel),
          adjust = "none"
        ))
        family_summary$plannedContrastId <- method_ids
        family_summary$multiplicityFamilyId <- family_id
        family_summary$multiplicityFamilySize <- length(method_ids)
        family_summary$pValueRaw <- family_summary$p.value
        family_summary$pValueAdjusted <- stats::p.adjust(
          family_summary$p.value,
          method = adjustment
        )
        # Holm and BH adjust the p-value family but do not define matching
        # simultaneous confidence limits.  Keep the individual interval and
        # state that scope explicitly instead of presenting it as adjusted.
        family_summary$p.value <- family_summary$pValueAdjusted
        family_summary$confidenceIntervalAdjustment <- "none_individual"
        family_summary$analysisRole <- "planned_contrast"
        family_summary$adjustment <- adjustment
        family_summary
      })
      planned_summary <- do.call(rbind, family_summaries)
      rownames(planned_summary) <- NULL
      if (nrow(planned_summary) != length(planned_methods)) {
        stop("PLANNED_CONTRAST_RESULT_COUNT_MISMATCH", call. = FALSE)
      }
      planned_summary <- planned_summary[
        match(names(planned_methods), planned_summary$plannedContrastId),
        ,
        drop = FALSE
      ]
      planned_contrast_rows <- rows(planned_summary)
      for (planned_row in planned_contrast_rows) {
        estimates[[length(estimates) + 1L]] <- estimate_entry(
          paste0("planned_", planned_row$plannedContrastId),
          paste0("Planned contrast: ", planned_row$plannedContrastId),
          planned_row$estimate,
          se = planned_row$SE,
          statistic = planned_row$t.ratio,
          df = planned_row$df,
          p = planned_row$p.value,
          lower = planned_row$lower.CL,
          upper = planned_row$upper.CL
        )
      }
    }
  }
  sphericity <- NULL
  if (length(within)) {
    sphericity <- tryCatch({
      summary_value <- summary(fit$Anova, multivariate = FALSE)
      list(
        tests = rows(as.data.frame(summary_value$sphericity.tests)),
        corrections = rows(as.data.frame(summary_value$pval.adjustments)),
        selectedCorrection = correction_method,
        primaryInference = omnibus
      )
    }, error = function(error) list(tests = list(), corrections = list(), message = conditionMessage(error)))
  }

  apaReports <- list(sprintf("An Analysis of Variance (ANOVA) was conducted on %s.", outcome))
  if (length(between) || length(within)) {
    apaReports[[length(apaReports) + 1L]] <- sprintf("Factors included %s.", paste(c(between, within), collapse = " and "))
  }
  if (length(omnibus)) {
    for (item in omnibus) {
      report_values <- list(
        numeratorDf = item$numeratorDf,
        denominatorDf = item$denominatorDf,
        f = item$f,
        pValue = item$pValue,
        partialEtaSquared = item$partialEtaSquared
      )
      missing_fields <- names(report_values)[!vapply(report_values, is_finite_scalar, logical(1))]
      if (length(missing_fields) == 0L) {
        apaReports[[length(apaReports) + 1L]] <- sprintf("For %s, F(%.2f, %.2f) = %.2f, p = %.3f, partial eta squared = %.3f.", item$term, item$numeratorDf, item$denominatorDf, item$f, item$pValue, item$partialEtaSquared)
      } else {
        apaReports[[length(apaReports) + 1L]] <- sprintf("For %s, the omnibus estimand was not fully estimable; unavailable fields: %s.", item$term, paste(missing_fields, collapse = ", "))
      }
    }
  }
  if (length(planned_contrast_rows)) {
    for (planned_row in planned_contrast_rows) {
      report_values <- list(
        estimate = planned_row$estimate,
        standardError = planned_row$SE,
        df = planned_row$df,
        pValue = planned_row$p.value,
        confidenceLower = planned_row$lower.CL,
        confidenceUpper = planned_row$upper.CL
      )
      missing_fields <- names(report_values)[!vapply(report_values, is_finite_scalar, logical(1))]
      if (length(missing_fields) == 0L) {
        apaReports[[length(apaReports) + 1L]] <- sprintf("For planned contrast %s in multiplicity family %s (m = %d), estimate = %.3f, SE = %.3f, df = %.2f, %s-adjusted p = %.3f, unadjusted individual %d%% CI [%.3f, %.3f].", planned_row$plannedContrastId, planned_row$multiplicityFamilyId, planned_row$multiplicityFamilySize, planned_row$estimate, planned_row$SE, planned_row$df, planned_row$adjustment, planned_row$p.value, as.integer(as.numeric(spec$confidenceLevel) * 100), planned_row$lower.CL, planned_row$upper.CL)
      } else {
        apaReports[[length(apaReports) + 1L]] <- sprintf("For planned contrast %s, the estimand was not fully estimable; unavailable fields: %s.", planned_row$plannedContrastId, paste(missing_fields, collapse = ", "))
      }
    }
  }

  plots <- list()

  list(
    sampleFlow = list(original = original_n, included = nrow(data), excluded = original_n - nrow(data), missingMethod = "complete cases"),
    estimates = estimates,
    diagnostics = diagnostics,
    warnings = warnings,
    provenance = list(engine = "R afex/emmeans", engineVersion = as.character(packageVersion("afex")), softwareVersions = package_versions(c("afex", "emmeans")), estimand = if (identical(spec$postHocAdjustment, "games_howell")) "unadjusted group mean differences with Games-Howell studentized-range inference" else "model-matrix marginal means", degreesOfFreedomMethod = "afex repeated-measures ANOVA", postHocMethod = spec$postHocAdjustment, plannedContrastCount = length(planned_contrast_rows)),
    familyResult = list(family = family, confidenceLevel = as.numeric(spec$confidenceLevel), omnibusTests = omnibus, estimatedMarginalMeans = emm_rows, contrasts = contrast_rows, plannedContrasts = planned_contrast_rows, sphericity = sphericity),
    apaReports = apaReports,
    plots = plots
  )
}

apply_centering <- function(data) {
  between_terms <- character(0)
  if (length(spec$centering) == 0L) return(list(data = data, between = between_terms))
  for (rule in spec$centering) {
    variable <- rule$variableId
    if (identical(rule$method, "grand_mean")) data[[variable]] <- data[[variable]] - mean(data[[variable]], na.rm = TRUE)
    if (identical(rule$method, "group_mean")) {
      group <- spec$clusterVariableId
      means <- ave(data[[variable]], data[[group]], FUN = function(x) mean(x, na.rm = TRUE))
      data[[paste0(variable, "__between")]] <- means
      data[[variable]] <- data[[variable]] - means
      between_terms <- c(between_terms, paste0(variable, "__between"))
    }
  }
  list(data = data, between = between_terms)
}


run_multilevel <- function() {
  suppressPackageStartupMessages(library(lme4))
  suppressPackageStartupMessages(library(lmerTest))
  suppressPackageStartupMessages(library(performance))
  if (!identical(spec$distribution, "gaussian")) stop("MLM_DISTRIBUTION_NOT_SUPPORTED")
  data <- read_analysis_data()
  centered <- apply_centering(data)
  data <- centered$data
  fixed <- unique(unlist(spec$fixedEffectIds))
  random_terms <- vapply(spec$randomEffects, function(effect) {
    slopes <- unlist(effect$slopeVariableIds)
    inside <- paste(c(if (isTRUE(effect$intercept)) "1" else "0", slopes), collapse = " + ")
    operator <- if (identical(effect$covariance, "diagonal")) "||" else "|"
    sprintf("(%s %s %s)", inside, operator, effect$groupingVariableId)
  }, character(1))
  formula <- as.formula(sprintf("%s ~ %s + %s", spec$outcomeId, paste(fixed, collapse = " + "), paste(random_terms, collapse = " + ")))
  selected <- unique(c(spec$outcomeId, fixed, spec$clusterVariableId, spec$higherLevelClusterVariableId, unlist(lapply(spec$randomEffects, function(x) x$slopeVariableIds))))
  selected <- selected[!is.na(selected) & nzchar(selected)]
  original_n <- nrow(data)
  data <- data[complete.cases(data[, selected, drop = FALSE]), , drop = FALSE]
  clusters <- length(unique(data[[spec$clusterVariableId]]))
  if (clusters < 2L) stop("Multilevel analysis requires at least two observed clusters")

  warnings <- list()
  for (rule in spec$centering) {
    if (identical(rule$method, "group_mean")) {
      between_var <- paste0(rule$variableId, "__between")
      if (!(between_var %in% spec$fixedEffectIds)) {
        warnings[[length(warnings) + 1L]] <- message_entry("MISSING_BETWEEN_EFFECT", "warning", sprintf("Group-mean centering was applied to '%s', but its cluster mean '%s' is not in fixed effects.", rule$variableId, between_var))
      }
    }
  }

  fit <- tryCatch(
    lmerTest::lmer(formula, data = data, REML = identical(spec$estimator, "REML")),
    error = function(error) {
      detail <- conditionMessage(error)
      if (grepl("not positive definite", detail, ignore.case = TRUE)) {
        stop("MLM_RANDOM_EFFECTS_MATRIX_NOT_POSITIVE_DEFINITE", call. = FALSE)
      }
      stop(sprintf("MLM_ESTIMATION_FAILED: %s", detail), call. = FALSE)
    }
  )
  convergence_messages <- unlist(fit@optinfo$conv$lme4$messages)
  convergence_failed <- length(convergence_messages) > 0L && any(grepl(
    "failed to converge|unable to evaluate scaled gradient|degenerate Hessian",
    convergence_messages,
    ignore.case = TRUE
  ))
  if (isTRUE(convergence_failed)) stop("MLM_NONCONVERGENCE", call. = FALSE)
  ddf_method <- switch(spec$degreesOfFreedom, satterthwaite = "Satterthwaite", kenward_roger = "Kenward-Roger", asymptotic = "lme4", "Satterthwaite")
  coefficients <- as.data.frame(coef(summary(fit, ddf = ddf_method)))
  coefficients$term <- rownames(coefficients)
  rownames(coefficients) <- NULL
  name_for <- function(pattern) {
    match <- grep(pattern, names(coefficients), ignore.case = TRUE, value = TRUE)
    if (length(match)) match[[1]] else NULL
  }
  estimate_col <- name_for("Estimate")
  se_col <- name_for("Std.*Error")
  statistic_col <- name_for("t value|z value")
  df_col <- name_for("^df$")
  p_col <- name_for("Pr\\(")
  critical_value <- function(df) {
    if (!is.null(df) && length(df) == 1L && is.finite(as.numeric(df)) && as.numeric(df) > 0) {
      return(qt(1 - (1 - as.numeric(spec$confidenceLevel)) / 2, df = as.numeric(df)))
    }
    qnorm(1 - (1 - as.numeric(spec$confidenceLevel)) / 2)
  }
  estimates <- lapply(seq_len(nrow(coefficients)), function(index) {
    estimate <- coefficients[[estimate_col]][[index]]
    se <- coefficients[[se_col]][[index]]
    df <- if (!is.null(df_col)) coefficients[[df_col]][[index]] else NULL
    critical <- critical_value(df)
    estimate_entry(coefficients$term[[index]], coefficients$term[[index]], estimate, se, coefficients[[statistic_col]][[index]], df, if (!is.null(p_col)) coefficients[[p_col]][[index]] else NULL, estimate - critical * se, estimate + critical * se, "outcome")
  })
  variances <- as.data.frame(VarCorr(fit))
  icc_value <- tryCatch(performance::icc(fit), error = function(error) NULL)
  icc_scalar <- if (is.null(icc_value)) NULL else finite(as.numeric(icc_value)[1L])
  r2_value <- tryCatch(performance::r2(fit), error = function(error) NULL)
  singular <- lme4::isSingular(fit)
  if (clusters < as.integer(spec$minimumClusterCount)) warnings[[length(warnings) + 1L]] <- message_entry("FEW_CLUSTERS", "warning", "Observed cluster count is below the declared minimum")
  if (singular) warnings[[length(warnings) + 1L]] <- message_entry("SINGULAR_FIT", "warning", "Random-effects covariance is singular and lies on a non-positive-definite boundary")

  apaReports <- list()
  apaReports[[1]] <- sprintf("A multilevel model was fitted to predict %s.", spec$outcomeId)
  if (!is.null(icc_scalar)) {
    apaReports[[length(apaReports) + 1L]] <- sprintf("The Intraclass Correlation Coefficient (ICC) was %.3f, indicating that %.1f%% of the variance is at the cluster level.", icc_scalar, icc_scalar * 100)
  }
  if (singular) {
    apaReports[[length(apaReports) + 1L]] <- "The random-effects covariance matrix is singular, suggesting the model may be over-parameterized."
  }

  list(
    sampleFlow = list(original = original_n, included = nrow(data), excluded = original_n - nrow(data), missingMethod = "complete cases", clusters = clusters),
    estimates = estimates,
    diagnostics = list(message_entry("MODEL_CONVERGENCE", if (singular) "warning" else "info", if (singular) "Model converged on a singular boundary" else "Model converged without a singular boundary")),
    warnings = warnings,
    provenance = list(engine = "R lme4/lmerTest/performance", engineVersion = as.character(packageVersion("lme4")), softwareVersions = package_versions(c("lme4", "lmerTest", "performance")), estimand = "conditional cluster-specific effect", degreesOfFreedomMethod = spec$degreesOfFreedom),
    familyResult = list(family = family, fixedEffects = rows(coefficients), randomEffects = rows(variances), varianceComponents = rows(variances), icc = if (is.null(icc_value)) list() else rows(as.data.frame(icc_value)), fitIndices = list(AIC = AIC(fit), BIC = BIC(fit), logLik = as.numeric(logLik(fit)), r2 = if (is.null(r2_value)) NULL else as.list(r2_value)), compiledFixedEffectIds = as.list(fixed)),
    apaReports = apaReports
  )
}

run_longitudinal <- function() {
  suppressPackageStartupMessages(library(lavaan))
  suppressPackageStartupMessages(library(lmerTest))
  data <- read_analysis_data()
  waves <- spec$waves
  stable_keys <- names(waves[[1]]$variables)
  original_n <- nrow(data)
  growth_singular <- FALSE
  all_vars <- unique(unlist(lapply(waves, function(w) unlist(w$variables))))
  if (identical(spec$missing, "available_rows_ml")) stop("LONGITUDINAL_AVAILABLE_ROWS_ML_NOT_IMPLEMENTED")
  if (identical(spec$modelType, "growth_curve") && identical(spec$missing, "fiml")) stop("LONGITUDINAL_FIML_NOT_SUPPORTED_FOR_OBSERVED_GROWTH")
  if (identical(spec$modelType, "ri_clpm")) {
    if (length(stable_keys) != 2L) stop("RI_CLPM_REQUIRES_TWO_CONSTRUCTS")
    x_waves <- vapply(waves, function(wave) wave$variables[[stable_keys[[1]]]], character(1))
    y_waves <- vapply(waves, function(wave) wave$variables[[stable_keys[[2]]]], character(1))
    ri_data <- data[, unique(c(x_waves, y_waves)), drop = FALSE]
    for (column in names(ri_data)) ri_data[[column]] <- suppressWarnings(as.numeric(ri_data[[column]]))
    ri_result <- tryCatch(
      fit_riclpm_model(ri_data, x_waves, y_waves, estimator = spec$estimator, missing = spec$missing),
      error = function(error) stop(paste0("RI_CLPM_ESTIMATION_FAILED: ", conditionMessage(error)))
    )
    wave_flow <- lapply(seq_along(waves), function(index) {
      current <- complete.cases(data[, unlist(waves[[index]]$variables), drop = FALSE])
      previous <- if (index == 1L) rep(TRUE, length(current)) else complete.cases(data[, unlist(waves[[index - 1L]]$variables), drop = FALSE])
      list(wave = waves[[index]]$wave, timeValue = waves[[index]]$timeValue, observed = sum(current), retainedFromPrevious = sum(previous & current), attritionFromPrevious = if (index == 1L) 0L else sum(previous & !current), attritionRateFromPrevious = if (index == 1L || sum(previous) == 0L) 0 else sum(previous & !current) / sum(previous), reenteredFromPrevious = if (index == 1L) 0L else sum(!previous & current))
    })
    parameters <- ri_result$crossLaggedEffects
    return(list(
      sampleFlow = list(original = original_n, included = ri_result$sampleSize, excluded = original_n - ri_result$sampleSize, missingMethod = spec$missing, waves = length(waves)),
      estimates = lapply(parameters, function(row) estimate_entry(paste0(row$lhs, "~", row$rhs), paste0(row$lhs, " ~ ", row$rhs), row$estimate, row$standardError, row$zValue, p = row$pValue, scale = "within_person")),
      diagnostics = list(message_entry("RI_CLPM_WAVE_SAMPLE_FLOW", "info", "RI-CLPM 返回逐波 attrition/re-entry 与 within-person cross-lagged parameters。")),
      warnings = list(),
      provenance = list(engine = "R lavaan RI-CLPM", engineVersion = as.character(packageVersion("lavaan")), softwareVersions = package_versions(c("lavaan")), estimand = "within-person autoregressive and cross-lagged effect with random intercepts", degreesOfFreedomMethod = "lavaan model based"),
      familyResult = list(family = family, modelType = spec$modelType, estimator = spec$estimator, missingMethod = spec$missing, timeValues = as.list(vapply(waves, function(wave) as.numeric(wave$timeValue), numeric(1))), parameters = parameters, autoregressiveEffects = ri_result$autoregressiveEffects, crossLaggedEffects = ri_result$crossLaggedEffects, traitComponents = ri_result$traitComponents, waveSampleFlow = wave_flow, fitIndices = ri_result$fitIndices, invariance = NULL, missingPatterns = ri_result$missingPatterns)
    ))
  }
  if (identical(spec$modelType, "longitudinal_invariance")) {
    source(file.path(script_dir, "lib", "invariance.R"), local = environment())
    syntax_lines <- character(0)
    for (key in stable_keys) {
      factor_name <- paste0("F_", key)
      wave_items <- vapply(waves, function(w) w$variables[[key]], character(1))
      syntax_lines <- c(syntax_lines, paste0(factor_name, " =~ ", paste(wave_items, collapse = " + ")))
    }
    model_syn <- paste(syntax_lines, collapse = "\n")
    group_var <- spec$groupVariableId
    if (is.null(group_var) || !group_var %in% names(data)) stop("LONGITUDINAL_INVARIANCE_GROUP_REQUIRED")
    res <- tryCatch(
      run_measurement_invariance(data, model_syn, group_var, estimator = spec$estimator, missing = spec$missing),
      error = function(e) stop(paste0("LONGITUDINAL_INVARIANCE_FAILED: ", conditionMessage(e)))
    )
    selected_levels <- unique(unlist(spec$invarianceLevels, use.names = FALSE))
    if (length(selected_levels) > 0L) {
      res$models <- res$models[names(res$models) %in% selected_levels]
      res$comparisons <- res$comparisons[names(res$comparisons) %in% selected_levels]
    }
    wave_flow <- lapply(seq_along(waves), function(index) {
      current <- complete.cases(data[, unlist(waves[[index]]$variables), drop = FALSE])
      previous <- if (index == 1L) rep(TRUE, length(current)) else complete.cases(data[, unlist(waves[[index - 1L]]$variables), drop = FALSE])
      list(
        wave = waves[[index]]$wave,
        timeValue = waves[[index]]$timeValue,
        observed = sum(current),
        retainedFromPrevious = sum(previous & current),
        attritionFromPrevious = if (index == 1L) 0L else sum(previous & !current),
        attritionRateFromPrevious = if (index == 1L || sum(previous) == 0L) 0 else sum(previous & !current) / sum(previous),
        reenteredFromPrevious = if (index == 1L) 0L else sum(!previous & current)
      )
    })
    latent_estimates <- if (length(res$latentMeans) == 0L) list() else lapply(res$latentMeans, function(row) {
      estimate_entry(
        paste(row$latentVariable, row$group, sep = "@"),
        paste(row$latentVariable, "group", row$group),
        row$estimate,
        row$se,
        row$zValue,
        p = row$pValue,
        scale = "latent_mean"
      )
    })
    return(list(
      sampleFlow = list(original = original_n, included = res$sampleSize, excluded = original_n - res$sampleSize, missingMethod = spec$missing, waves = length(waves)),
      estimates = latent_estimates,
      diagnostics = list(message_entry("LONGITUDINAL_INVARIANCE_COMPLETED", "info", "Longitudinal measurement invariance levels were fitted with an explicit group variable.")),
      warnings = list(),
      provenance = list(engine = "R lavaan longitudinal invariance", engineVersion = as.character(packageVersion("lavaan")), softwareVersions = package_versions(c("lavaan")), estimand = "cross-wave measurement invariance and latent mean differences", degreesOfFreedomMethod = "lavaan model based"),
      familyResult = list(family = family, modelType = spec$modelType, estimator = spec$estimator, missingMethod = spec$missing, timeValues = as.list(vapply(waves, function(wave) as.numeric(wave$timeValue), numeric(1))), parameters = list(), waveSampleFlow = wave_flow, fitIndices = if (is.null(res$models$configural)) list() else res$models$configural, invariance = res, missingPatterns = NULL)
    ))
  }
  if (identical(spec$modelType, "growth_curve")) {
    key <- stable_keys[[1]]
    growth_data <- data
    if (identical(spec$missing, "complete_cases")) {
      growth_variables <- vapply(waves, function(wave) wave$variables[[key]], character(1))
      growth_data <- data[complete.cases(data[, growth_variables, drop = FALSE]), , drop = FALSE]
    }
    pieces <- lapply(waves, function(wave) data.frame(subject = growth_data[[spec$subjectId]], time = as.numeric(wave$timeValue), outcome = growth_data[[wave$variables[[key]]]]))
    long <- do.call(rbind, pieces)
    long <- long[complete.cases(long), , drop = FALSE]
    fit <- tryCatch(
      lmerTest::lmer(outcome ~ time + (time | subject), data = long, REML = FALSE),
      error = function(error) {
        detail <- conditionMessage(error)
        if (grepl("not positive[- ]definite|non-positive[- ]definite", detail, ignore.case = TRUE)) {
          stop("LONGITUDINAL_SAMPLE_COVARIANCE_NOT_POSITIVE_DEFINITE", call. = FALSE)
        }
        stop(sprintf("LONGITUDINAL_ESTIMATION_FAILED: %s", detail), call. = FALSE)
      }
    )
    growth_convergence_messages <- unlist(fit@optinfo$conv$lme4$messages)
    growth_convergence_failed <- length(growth_convergence_messages) > 0L && any(grepl(
      "failed to converge|unable to evaluate scaled gradient|degenerate Hessian",
      growth_convergence_messages,
      ignore.case = TRUE
    ))
    if (isTRUE(growth_convergence_failed)) stop("LONGITUDINAL_NONCONVERGENCE", call. = FALSE)
    growth_singular <- isTRUE(lme4::isSingular(fit))
    coefficients <- as.data.frame(coef(summary(fit)))
    coefficients$term <- rownames(coefficients)
    estimates <- lapply(seq_len(nrow(coefficients)), function(index) estimate_entry(coefficients$term[[index]], coefficients$term[[index]], coefficients$Estimate[[index]], coefficients$`Std. Error`[[index]], coefficients$`t value`[[index]], coefficients$df[[index]], coefficients$`Pr(>|t|)`[[index]], scale = "outcome"))
    parameters <- rows(coefficients)
    fit_indices <- list(AIC = AIC(fit), BIC = BIC(fit), logLik = as.numeric(logLik(fit)))
    included_subjects <- length(unique(long$subject))
    engine <- "R lmerTest"
    versions <- package_versions(c("lmerTest", "lme4"))
  } else {
    if (identical(spec$modelType, "cross_lagged_panel") && length(waves) < 3L) stop("LONGITUDINAL_INSUFFICIENT_WAVES_FOR_SUPPORTED_CLPM")
    syntax <- character(0)
    if (identical(spec$modelType, "latent_growth")) {
      for (key in stable_keys) {
        variables <- vapply(waves, function(wave) wave$variables[[key]], character(1))
        times <- vapply(waves, function(wave) as.numeric(wave$timeValue), numeric(1))
        syntax <- c(syntax, sprintf("i_%s =~ %s", key, paste(sprintf("1*%s", variables), collapse = " + ")), sprintf("s_%s =~ %s", key, paste(sprintf("%s*%s", times, variables), collapse = " + ")))
      }
    } else {
      for (index in 2:length(waves)) {
        previous <- unlist(waves[[index - 1]]$variables)
        current <- unlist(waves[[index]]$variables)
        for (key in names(current)) syntax <- c(syntax, sprintf("%s ~ %s", current[[key]], paste(previous, collapse = " + ")))
        if (length(current) > 1L) syntax <- c(syntax, paste(current, collapse = " ~~ "))
      }
    }
    fit <- tryCatch(
      lavaan::sem(paste(syntax, collapse = "\n"), data = data, estimator = spec$estimator, missing = if (identical(spec$missing, "fiml")) "fiml" else "listwise"),
      error = function(error) {
        detail <- conditionMessage(error)
        if (grepl("not positive[- ]definite|non-positive[- ]definite", detail, ignore.case = TRUE)) {
          stop("LONGITUDINAL_SAMPLE_COVARIANCE_NOT_POSITIVE_DEFINITE", call. = FALSE)
        }
        stop(sprintf("LONGITUDINAL_ESTIMATION_FAILED: %s", detail), call. = FALSE)
      }
    )
    if (!lavInspect(fit, "converged")) stop("LONGITUDINAL_NONCONVERGENCE", call. = FALSE)
    if (!isTRUE(lavInspect(fit, "post.check"))) stop("LONGITUDINAL_POST_ESTIMATION_INVALID", call. = FALSE)
    parameter_table <- parameterEstimates(fit, ci = TRUE, level = as.numeric(spec$confidenceLevel))
    structural <- parameter_table[parameter_table$op %in% c("~", "=~"), , drop = FALSE]
    estimates <- lapply(seq_len(nrow(structural)), function(index) estimate_entry(paste(structural$lhs[[index]], structural$op[[index]], structural$rhs[[index]]), paste(structural$lhs[[index]], structural$op[[index]], structural$rhs[[index]]), structural$est[[index]], structural$se[[index]], structural$z[[index]], NULL, structural$pvalue[[index]], structural$ci.lower[[index]], structural$ci.upper[[index]], "model"))
    parameters <- rows(structural)
    fit_indices <- as.list(fitMeasures(fit, c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr", "aic", "bic")))
    included_subjects <- lavInspect(fit, "ntotal")
    engine <- "R lavaan"
    versions <- package_versions(c("lavaan"))
  }
  missing_patterns <- NULL
  if (exists("fit") && inherits(fit, "lavaan") && identical(spec$missing, "fiml")) {
    pattern_matrix <- lavInspect(fit, "patterns")
    missing_patterns <- jsonlite::toJSON(unname(split(as.data.frame(pattern_matrix), seq_len(nrow(pattern_matrix)))), auto_unbox = TRUE)
  }

  wave_observed <- lapply(waves, function(wave) complete.cases(data[, unlist(wave$variables), drop = FALSE]))
  wave_flow <- lapply(seq_along(waves), function(index) {
    current <- wave_observed[[index]]
    previous <- if (index == 1L) rep(TRUE, length(current)) else wave_observed[[index - 1L]]
    list(
      wave = waves[[index]]$wave,
      timeValue = waves[[index]]$timeValue,
      observed = sum(current),
      retainedFromPrevious = sum(previous & current),
      attritionFromPrevious = if (index == 1L) 0L else sum(previous & !current),
      attritionRateFromPrevious = if (index == 1L || sum(previous) == 0L) 0 else sum(previous & !current) / sum(previous),
      reenteredFromPrevious = if (index == 1L) 0L else sum(!previous & current)
    )
  })
  list(
    sampleFlow = list(original = original_n, included = as.integer(included_subjects), excluded = original_n - as.integer(included_subjects), missingMethod = spec$missing, waves = length(waves)),
    estimates = estimates,
    diagnostics = list(message_entry("WAVE_SAMPLE_FLOW", "info", "Per-wave observed counts are reported in familyResult")),
    warnings = c(
      if (length(stable_keys) > 1L && identical(spec$modelType, "growth_curve")) list(message_entry("GROWTH_FIRST_OUTCOME", "warning", "Growth curve execution used the first stable outcome key; run separate specifications for additional outcomes")) else list(),
      if (isTRUE(growth_singular)) list(message_entry("LONGITUDINAL_SINGULAR_FIT", "warning", "Growth curve random-slope variance lies on the singular boundary; the time slope and its confidence interval may be unreliable.")) else list()
    ),
    provenance = list(engine = engine, engineVersion = unlist(versions)[[1]], softwareVersions = versions, estimand = if (identical(spec$modelType, "growth_curve")) "population-average time slope with subject random effects" else "longitudinal structural parameter", degreesOfFreedomMethod = "model based"),
    familyResult = list(family = family, modelType = spec$modelType, estimator = spec$estimator, missingMethod = spec$missing, timeValues = as.list(vapply(waves, function(wave) as.numeric(wave$timeValue), numeric(1))), parameters = parameters, waveSampleFlow = wave_flow, fitIndices = fit_indices, invariance = NULL, missingPatterns = if (!is.null(missing_patterns)) as.character(missing_patterns) else NULL)
  )
}


write_progress("preparing_advanced_analysis", 0.05)
result <- switch(
  family,
  power_analysis = run_power(),
  experimental_design = run_experimental(),
  multilevel_model = if (identical(spec$analysisType, "aggregation")) run_aggregation() else run_multilevel(),
  longitudinal_model = run_longitudinal(),
  multiple_imputation = run_imputation(),
  questionnaire_measurement = run_questionnaire_measurement(),
  stop("Unknown advanced analysis family")
)
write_progress("succeeded", 1.0)
researchpath_write_result(result, args[[2]])
