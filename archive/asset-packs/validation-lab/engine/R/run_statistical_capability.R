args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_statistical_capability.R <input.json> <output.json>")

script_arg <- commandArgs(trailingOnly = FALSE)
script_file <- sub("^--file=", "", script_arg[grepl("^--file=", script_arg)])
script_dir <- dirname(normalizePath(script_file, winslash = "/", mustWork = TRUE))
lib_dir <- file.path(script_dir, "lib")

suppressPackageStartupMessages(library(jsonlite))
source(file.path(lib_dir, "runtime.R"), local = environment())
source(file.path(lib_dir, "experiment_posthoc.R"), local = environment())
source(file.path(lib_dir, "mi_rubin.R"), local = environment())
source(file.path(lib_dir, "multilevel_aggregation.R"), local = environment())
source(file.path(lib_dir, "tost_multiplicity.R"), local = environment())

request <- jsonlite::fromJSON(args[[1]], simplifyVector = FALSE)
capability_id <- request$capabilityId
spec <- request$spec
data <- utils::read.csv(request$dataPath, check.names = FALSE, stringsAsFactors = FALSE)

failure <- function(reason_code, message) list(
  status = "failed",
  failure = list(reasonCode = reason_code, message = message,
    mustNotReturnEstimates = TRUE, mustNotFallback = TRUE)
)

result <- switch(capability_id,
  "imputation.pooling.linear.rubin.v1" = {
    if (!all(c("q", "u") %in% names(data))) {
      failure("RUBIN_INPUT_COLUMNS_MISSING", "Rubin pooling requires q and u columns")
    } else if (nrow(data) < 2L) {
      failure("RUBIN_TOO_FEW_IMPUTATIONS", "Rubin pooling requires at least two imputations")
    } else if (any(!is.finite(as.numeric(data$q))) || any(!is.finite(as.numeric(data$u))) || any(as.numeric(data$u) <= 0)) {
      failure("RUBIN_INVALID_WITHIN_VARIANCE", "Estimates and within variances must be finite, with positive variance")
    } else {
      complete_df <- if (!is.null(spec$completeDataDf)) rep(as.numeric(spec$completeDataDf), nrow(data)) else NULL
      pooled <- pool_rubin_estimates(as.numeric(data$q), sqrt(as.numeric(data$u)), complete_df)
      list(
        pooled_estimate = pooled$pooledEstimate,
        within_variance = pooled$withinVariance,
        between_variance = pooled$betweenVariance,
        total_variance = pooled$totalVariance,
        se = pooled$pooledSE,
        relative_increase_variance = pooled$RIV,
        df = pooled$degreesOfFreedom
      )
    }
  },
  "power.t_test.analytic.v1" = {
    n1 <- as.integer(spec$n1); n2 <- as.integer(spec$n2)
    alpha <- as.numeric(spec$alpha); effect <- as.numeric(spec$effectSize)
    alternative <- as.character(spec$alternative)
    failure <- function(reason_code, message) list(failure = list(
      status = "failed", reasonCode = reason_code, message = message,
      mustNotReturnEstimates = TRUE, mustNotFallback = TRUE
    ))
    if (!identical(as.character(spec$testType), "two_sample")) {
      failure("UNSUPPORTED_TEST_TYPE", "Only independent two-sample t-test power is supported")
    } else if (!identical(alternative, "two_sided")) {
      failure("UNSUPPORTED_ALTERNATIVE", "Only two-sided t-test power is supported")
    } else if (length(alpha) != 1L || !is.finite(alpha) || alpha <= 0 || alpha >= 1) {
      failure("INVALID_ALPHA", "alpha must be finite and strictly between 0 and 1")
    } else if (length(n1) != 1L || length(n2) != 1L || is.na(n1) || is.na(n2) || n1 < 2L || n2 < 2L) {
      failure("INVALID_SAMPLE_SIZE", "n1 and n2 must both be integers greater than or equal to 2")
    } else if (length(effect) != 1L || !is.finite(effect)) {
      failure("INVALID_EFFECT_SIZE", "effectSize must be finite")
    } else {
      degrees <- n1 + n2 - 2L
      ncp <- effect * sqrt(n1 * n2 / (n1 + n2))
      critical <- stats::qt(1 - alpha / 2, df = degrees)
      power <- stats::pt(-critical, df = degrees, ncp = ncp) +
        1 - stats::pt(critical, df = degrees, ncp = ncp)
      list(testType = spec$testType, effectSize = effect, alpha = alpha, n1 = n1, n2 = n2,
        df = degrees, ncp = ncp, power = power)
    }
  },
  "power.regression.f2.analytic.v1" = {
    effect <- as.numeric(spec$f2); u <- as.integer(spec$u); v <- as.integer(spec$v)
    alpha <- as.numeric(spec$alpha)
    if (!is.finite(effect) || effect < 0 || is.na(u) || u < 1L || is.na(v) || v < 1L) {
      failure("POWER_INVALID_DEGREES_OF_FREEDOM", "f2 must be non-negative and u/v must both be positive")
    } else if (!is.finite(alpha) || alpha <= 0 || alpha >= 1) {
      failure("POWER_INVALID_ALPHA", "alpha must be strictly between zero and one")
    } else {
      ncp <- effect * (u + v + 1)
      critical <- stats::qf(1 - alpha, df1 = u, df2 = v)
      list(f2 = effect, u = u, v = v, n = as.integer(u + v + 1L), alpha = alpha, ncp = ncp, f_crit = critical,
        power = 1 - stats::pf(critical, df1 = u, df2 = v, ncp = ncp))
    }
  },
  "multilevel.icc.two_level.v1" = {
    outcome <- spec$outcomeVariable; cluster <- spec$clusterVariable
    frame <- data[stats::complete.cases(data[, c(outcome, cluster)]), , drop = FALSE]
    cluster_factor <- factor(frame[[cluster]])
    fit_frame <- data.frame(.rp_outcome = as.numeric(frame[[outcome]]), .rp_cluster = cluster_factor)
    fit_table <- summary(stats::aov(.rp_outcome ~ .rp_cluster, data = fit_frame))[[1]]
    ms_between <- as.numeric(fit_table["Mean Sq"][1, 1])
    ms_within <- as.numeric(fit_table["Mean Sq"][2, 1])
    sizes <- as.numeric(table(cluster_factor)); n_total <- sum(sizes)
    n_bar <- (n_total - sum(sizes^2) / n_total) / (length(sizes) - 1)
    var_between <- (ms_between - ms_within) / n_bar
    list(cluster_count = length(sizes), cluster_size = if (length(unique(sizes)) == 1L) sizes[[1]] else NULL,
      ms_between = ms_between, ms_within = ms_within, var_between = var_between,
      var_within = ms_within,
      icc1 = (ms_between - ms_within) / (ms_between + (n_bar - 1) * ms_within),
      icc2 = (ms_between - ms_within) / ms_between)
  },
  "equivalence.tost.two_sample.v1" = {
    parameters <- spec$parameters
    low <- as.numeric(parameters$lowBound); high <- as.numeric(parameters$highBound)
    alpha <- as.numeric(parameters$alpha)
    method <- if (is.null(parameters$varianceMethod)) "student" else as.character(parameters$varianceMethod)
    if (!is.finite(low) || !is.finite(high) || low >= high) {
      failure("TOST_INVALID_BOUNDS", "The lower equivalence bound must be strictly less than the upper bound")
    } else if (!all(c(spec$data$outcomeVar, spec$data$groupVar) %in% names(data)) || length(unique(stats::na.omit(data[[spec$data$groupVar]]))) != 2L) {
      failure("TOST_INVALID_GROUP_LAYOUT", "TOST requires exactly two observed groups")
    } else if (any(table(stats::na.omit(data[[spec$data$groupVar]])) < 2L)) {
      failure("TOST_INSUFFICIENT_SAMPLE", "Each TOST group requires at least two observations")
    } else {
      value <- tryCatch(run_tost_equivalence(data, spec$data$outcomeVar, spec$data$groupVar, low, high, alpha, method),
        error = function(error) error)
      if (inherits(value, "error")) failure("TOST_ESTIMATION_FAILED", conditionMessage(value)) else list(
        tost_results = list(mean_diff = value$meanDifference, se = value$standardError, df = value$degreesOfFreedom,
          variance_method = value$varianceMethod, t_lower = value$t1, p_lower = value$p1,
          t_upper = value$t2, p_upper = value$p2, tost_p = value$pTOST,
          equivalent = value$equivalent, decision = if (isTRUE(value$equivalent)) "equivalent" else "not_equivalent"),
        diagnostics = list(converged = TRUE))
    }
  },
  "experiment.posthoc.games_howell.v1" = {
    outcome <- spec$data$outcomeVar; group <- spec$data$groupVar
    if (!all(c(outcome, group) %in% names(data)) || length(unique(stats::na.omit(data[[group]]))) < 2L) {
      failure("GAMES_HOWELL_REQUIRES_TWO_GROUPS", "Games-Howell requires at least two observed groups")
    } else if (any(table(stats::na.omit(data[[group]])) < 2L)) {
      failure("GAMES_HOWELL_GROUP_REQUIRES_TWO_OBSERVATIONS", "Each Games-Howell group requires at least two observations")
    } else {
      rows <- fit_games_howell(data, outcome, group, 1 - as.numeric(spec$parameters$alpha))
      list(contrasts = lapply(rows, function(row) list(comparison = row$contrast,
        estimate = row$estimate, se = row$standardError, df = row$degreesOfFreedom,
        q_statistic = row$qStatistic, p_adjusted = row$pValue,
        ci_lower = row$confidenceLower, ci_upper = row$confidenceUpper)),
        diagnostics = list(converged = TRUE))
    }
  },
  "experiment.randomization.inference.v1" = {
    treatment_name <- spec$data$treatmentVar; outcome_name <- spec$data$outcomeVar
    block_name <- spec$data$blockVar
    if (!all(c(treatment_name, outcome_name) %in% names(data))) {
      failure("RANDOMIZATION_COLUMNS_MISSING", "Treatment and outcome columns are required")
    } else if (!is.null(spec$parameters$assignmentLength) && as.integer(spec$parameters$assignmentLength) != nrow(data)) {
      failure("RANDOMIZATION_ASSIGNMENT_LENGTH_MISMATCH", "Assignment length does not match the outcome vector")
    } else {
      treatment <- as.numeric(data[[treatment_name]]); outcome <- as.numeric(data[[outcome_name]])
      if (any(!is.finite(treatment)) || any(!is.finite(outcome)) || !all(treatment %in% c(0, 1)) || !any(treatment == 1) || !any(treatment == 0)) {
        failure("RANDOMIZATION_INVALID_ASSIGNMENT", "Treatment must contain both binary assignment values")
      } else if (!is.null(block_name) && !block_name %in% names(data)) {
        failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Declared block variable is missing")
      } else {
        blocks <- if (is.null(block_name)) list(all = seq_along(outcome)) else split(seq_along(outcome), data[[block_name]])
        option_sets <- lapply(blocks, function(indices) {
          treated <- sum(treatment[indices] == 1)
          if (treated < 1L || treated >= length(indices)) return(NULL)
          utils::combn(indices, treated, simplify = FALSE)
        })
        if (any(vapply(option_sets, is.null, logical(1)))) {
          failure("RANDOMIZATION_INVALID_BLOCK_STRUCTURE", "Every block requires treated and control observations")
        } else {
          assignments <- list(integer(0))
          for (options in option_sets) assignments <- unlist(lapply(assignments, function(prefix) lapply(options, function(next_indices) c(prefix, next_indices))), recursive = FALSE)
          observed <- mean(outcome[treatment == 1]) - mean(outcome[treatment == 0])
          statistics <- vapply(assignments, function(indices) mean(outcome[indices]) - mean(outcome[-indices]), numeric(1))
          list(ate = observed, permutation_count = length(assignments),
            p_value_two_sided = mean(abs(statistics) >= abs(observed) - 1e-12),
            p_value_one_sided = mean(statistics >= observed - 1e-12),
            diagnostics = list(converged = TRUE))
        }
      }
    }
  },
  "multilevel.lmm.within_between.v1" = {
    cluster <- spec$data$clusterVar; predictor <- spec$data$predictor; outcome <- spec$data$outcome
    between <- ave(data[[predictor]], data[[cluster]], FUN = mean)
    within <- data[[predictor]] - between
    model_data <- data.frame(y = data[[outcome]], x_within = within, x_between = between)
    fit <- stats::lm(y ~ x_within + x_between, data = model_data)
    table <- summary(fit)$coefficients
    list(fixed_effects = lapply(seq_len(nrow(table)), function(index) list(
      term = rownames(table)[[index]], estimate = unname(table[index, "Estimate"]),
      se = unname(table[index, "Std. Error"]), statistic = unname(table[index, "t value"]),
      p_value = unname(table[index, "Pr(>|t|)"]))), diagnostics = list(converged = TRUE))
  },
  "longitudinal.esm.diary_ar1.v1" = {
    person <- spec$data$personVar; day <- spec$data$dayVar
    prompt <- spec$data$promptVar; outcome <- spec$data$outcome
    frame <- data.frame(y = as.numeric(data[[outcome]]), person = factor(data[[person]]),
      day = factor(data[[day]]), prompt = as.numeric(data[[prompt]]))
    frame$person_day <- interaction(frame$person, frame$day, drop = TRUE)
    fit <- nlme::lme(y ~ 1, random = ~1 | person, data = frame, method = "REML",
      correlation = nlme::corAR1(form = ~prompt | person/person_day),
      control = nlme::lmeControl(returnObject = TRUE, maxIter = 200L))
    variance <- nlme::VarCorr(fit)
    list(ar1_phi = as.numeric(coef(fit$modelStruct$corStruct, unconstrained = FALSE)[[1]]),
      within_variance = as.numeric(fit$sigma)^2,
      between_variance = as.numeric(variance[1, "Variance"]),
      fixed_intercept = as.numeric(nlme::fixef(fit)[[1]]),
      diagnostics = list(converged = is.null(fit$fail)))
  },
  "multilevel.se.cluster_robust.v1" = {
    cluster <- spec$data$clusterVar; predictor <- spec$data$predictor; outcome <- spec$data$outcome
    fit <- stats::lm(stats::reformulate(predictor, response = outcome), data = data)
    test <- clubSandwich::coef_test(fit, vcov = "CR2", cluster = data[[cluster]], test = "Satterthwaite")
    list(fixed_effects = lapply(seq_len(nrow(test)), function(index) list(
      term = rownames(test)[[index]], estimate = as.numeric(test$beta[[index]]),
      se_cr2 = as.numeric(test$SE[[index]]), df_satt = as.numeric(test$df_Satt[[index]]),
      statistic = as.numeric(test$tstat[[index]]), p_value = as.numeric(test$p_Satt[[index]]))),
      cluster_info = list(num_clusters = length(unique(data[[cluster]])), vcov_type = "CR2"),
      diagnostics = list(converged = TRUE))
  },
  "multilevel.mediation.two_level.v1" = {
    cluster <- spec$data$clusterVar; x <- spec$data$x; mediator <- spec$data$m; outcome <- spec$data$y
    cluster_factor <- factor(data[[cluster]])
    x_between <- ave(data[[x]], cluster_factor, FUN = mean); x_within <- data[[x]] - x_between
    m_between <- ave(data[[mediator]], cluster_factor, FUN = mean); m_within <- data[[mediator]] - m_between
    frame <- data.frame(y = data[[outcome]], m = data[[mediator]], x_between, x_within,
      m_between, m_within, cluster = cluster_factor)
    mediator_fit <- lme4::lmer(m ~ x_between + x_within + (1 | cluster), data = frame, REML = FALSE)
    outcome_fit <- lme4::lmer(y ~ x_between + x_within + m_between + m_within + (1 | cluster),
      data = frame, REML = FALSE)
    a <- lme4::fixef(mediator_fit); b <- lme4::fixef(outcome_fit)
    a_se <- sqrt(diag(as.matrix(stats::vcov(mediator_fit)))); b_se <- sqrt(diag(as.matrix(stats::vcov(outcome_fit))))
    indirect <- function(level, a_name, b_name) {
      estimate <- as.numeric(a[[a_name]] * b[[b_name]])
      standard_error <- sqrt((b[[b_name]]^2 * a_se[[a_name]]^2) + (a[[a_name]]^2 * b_se[[b_name]]^2))
      set.seed(if (is.null(spec$parameters$seed)) 20260723L else as.integer(spec$parameters$seed))
      draws <- stats::rnorm(50000L, a[[a_name]], a_se[[a_name]]) * stats::rnorm(50000L, b[[b_name]], b_se[[b_name]])
      interval <- stats::quantile(draws, c(0.025, 0.975), names = FALSE)
      z <- estimate / standard_error
      list(estimate = estimate, se = standard_error, ci_lower = interval[[1]], ci_upper = interval[[2]],
        p_value = 2 * stats::pnorm(-abs(z)))
    }
    list(indirect_effects = list(
      between = indirect("between", "x_between", "m_between"),
      within = indirect("within", "x_within", "m_within")),
      diagnostics = list(converged = identical(mediator_fit@optinfo$conv$opt, 0) &&
        identical(outcome_fit@optinfo$conv$opt, 0)))
  },
  "robustness.specification_curve.matrix.v1" = {
    x <- spec$data$x; y <- spec$data$y; covariates <- unlist(spec$data$covariates)
    covariate_sets <- if (is.null(covariates) || length(covariates) == 0L) list(character(0)) else unlist(lapply(0:length(covariates), function(size) {
      utils::combn(covariates, size, simplify = FALSE)
    }), recursive = FALSE)
    base_fit <- stats::lm(stats::reformulate(x, response = y), data = data)
    keep_trimmed <- abs(stats::rstandard(base_fit)) <= 2.5
    specifications <- list(); index <- 1L
    for (model_type in unlist(spec$parameters$modelTypes)) for (subset_name in unlist(spec$parameters$subsets)) for (controls in covariate_sets) {
      frame <- if (identical(subset_name, "trimmed")) data[keep_trimmed, , drop = FALSE] else data
      formula <- stats::reformulate(c(x, controls), response = y)
      if (identical(model_type, "ols")) {
        table <- summary(stats::lm(formula, data = frame))$coefficients
        estimate <- table[x, "Estimate"]; standard_error <- table[x, "Std. Error"]; p_value <- table[x, "Pr(>|t|)"]
      } else {
        table <- summary(MASS::rlm(formula, data = frame, maxit = 100L))$coefficients
        estimate <- table[x, "Value"]; standard_error <- table[x, "Std. Error"]
        p_value <- 2 * stats::pnorm(-abs(estimate / standard_error))
      }
      specifications[[index]] <- list(spec_id = sprintf("spec_%02d", index), model_type = model_type,
        subset = subset_name, covariates = as.list(controls), estimate = as.numeric(estimate),
        se = as.numeric(standard_error), p_value = as.numeric(p_value))
      index <- index + 1L
    }
    estimates <- vapply(specifications, `[[`, numeric(1), "estimate")
    p_values <- vapply(specifications, `[[`, numeric(1), "p_value")
    list(total_specifications = length(specifications), median_effect = stats::median(estimates),
      significant_ratio = mean(p_values < 0.05), specifications_summary = specifications,
      diagnostics = list(converged = TRUE))
  },
  stop(paste0("STATISTICAL_CAPABILITY_NOT_IMPLEMENTED: ", capability_id), call. = FALSE)
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE,
  null = "null", na = "null", digits = NA)
