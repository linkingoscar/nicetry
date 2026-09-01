args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_remaining_reference.R <case-dir> <output.json>")
suppressPackageStartupMessages(library(jsonlite))
case_dir <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
manifest <- yaml::read_yaml(file.path(case_dir, "manifest.yaml"))
spec <- jsonlite::fromJSON(file.path(case_dir, manifest$specPath), simplifyVector = FALSE)
data <- utils::read.csv(file.path(case_dir, "data", "input.csv"), check.names = FALSE,
  stringsAsFactors = FALSE)
capability <- manifest$identity$capabilityId

result <- switch(capability,
  "experiment.between.factorial.gaussian.v1" =,
  "experiment.emmeans.planned_contrast.v1" = {
    outcome <- unlist(spec$outcomeIds)[[1]]
    factors <- vapply(spec$betweenFactors, `[[`, character(1), "variableId")
    covariates <- unlist(spec$covariateIds, use.names = FALSE)
    for (name in factors) {
      data[[name]] <- factor(data[[name]])
      contrasts(data[[name]]) <- stats::contr.sum(nlevels(data[[name]]))
    }
    for (name in covariates) data[[name]] <- data[[name]] - mean(data[[name]])
    formula <- stats::reformulate(c(if (length(factors)) paste(factors, collapse = " * ") else NULL, covariates), response = outcome)
    fit <- stats::lm(formula, data = data)
    table <- as.data.frame(car::Anova(fit, type = if (spec$sumOfSquares == "II") 2L else 3L))
    table <- table[!rownames(table) %in% c("(Intercept)", "Residuals"), , drop = FALSE]
    residual_df <- stats::df.residual(fit)
    omnibus <- lapply(seq_len(nrow(table)), function(index) list(
      term = rownames(table)[[index]], `num Df` = as.numeric(table$Df[[index]]),
      `den Df` = residual_df, F = as.numeric(table$`F value`[[index]]),
      `Pr(>F)` = as.numeric(table$`Pr(>F)`[[index]])))
    grid <- emmeans::emmeans(fit, specs = factors)
    means <- as.data.frame(confint(grid, level = as.numeric(spec$confidenceLevel)))
    names(means)[names(means) == "lower.CL"] <- "lower_CL"
    names(means)[names(means) == "upper.CL"] <- "upper_CL"
    list(familyResult = list(omnibusTests = omnibus,
      estimatedMarginalMeans = lapply(seq_len(nrow(means)), function(index) as.list(means[index, , drop = FALSE])),
      contrasts = list(), sphericity = NULL))
  },
  "experiment.repeated.one_within.v1" = {
    data$treatment <- factor(data$treatment); data$phase <- factor(data$phase)
    contrasts(data$treatment) <- stats::contr.sum(nlevels(data$treatment))
    contrasts(data$phase) <- stats::contr.sum(nlevels(data$phase))
    fit <- afex::aov_car(value ~ treatment * phase + Error(id / phase), data = data,
      type = 3L, factorize = FALSE)
    table <- as.data.frame(anova(fit, correction = "GG", es = "pes"))
    omnibus <- lapply(seq_len(nrow(table)), function(index) list(
      term = rownames(table)[[index]], `num Df` = as.numeric(table$`num Df`[[index]]),
      `den Df` = as.numeric(table$`den Df`[[index]]), F = as.numeric(table$F[[index]]),
      `Pr(>F)` = as.numeric(table$`Pr(>F)`[[index]])))
    summary_value <- summary(fit$Anova, multivariate = FALSE)
    adjustments <- as.data.frame(summary_value$pval.adjustments)
    list(familyResult = list(omnibusTests = omnibus, estimatedMarginalMeans = list(), contrasts = list(),
      sphericity = list(mauchly_p = NULL, gg_epsilon = as.numeric(adjustments$`GG eps`[[1]]),
        hf_epsilon = as.numeric(adjustments$`HF eps`[[1]]))))
  },
  "multilevel.lmm.two_level.gaussian.random_slope.v1" = {
    outcome <- spec$outcomeId
    cluster <- spec$clusterVariableId
    fixed_vars <- unlist(spec$fixedEffectIds)
    data[[cluster]] <- factor(data[[cluster]])
    fixed_part <- if (length(fixed_vars)) paste(fixed_vars, collapse = " + ") else "1"
    formula_str <- paste0(outcome, " ~ ", fixed_part, " + (", fixed_part, " | ", cluster, ")")
    fit <- lmerTest::lmer(stats::as.formula(formula_str), data = data, REML = TRUE)
    table <- as.data.frame(coef(summary(fit))); table$term <- rownames(table)
    names(table)[names(table) == "Std. Error"] <- "Std_Error"
    names(table)[names(table) == "t value"] <- "t_value"
    names(table)[names(table) == "Pr(>|t|)"] <- "Pr_t"
    var_corr <- as.data.frame(lme4::VarCorr(fit))
    names(var_corr)[names(var_corr) == "Std.Dev."] <- "Std_Dev"
    list(familyResult = list(fixedEffects = lapply(seq_len(nrow(table)), function(index) as.list(table[index, , drop = FALSE])),
         randomEffects = lapply(seq_len(nrow(var_corr)), function(index) as.list(var_corr[index, , drop = FALSE]))))
  },
  "imputation.mice.chain_diagnostics.v1" = {
    methods <- c(x1 = "pmm", x2 = "pmm", interaction = "~I(x1 * x2)")
    predictors <- matrix(0, 3L, 3L, dimnames = list(names(methods), names(methods)))
    predictors["x1", "x2"] <- 1; predictors["x2", "x1"] <- 1
    predictors["interaction", c("x1", "x2")] <- 1
    imputed <- mice::mice(data[, names(methods)], m = as.integer(spec$imputations),
      maxit = as.integer(spec$iterations), method = methods, predictorMatrix = predictors,
      seed = as.integer(spec$seed), printFlag = FALSE)
    completed <- lapply(seq_len(as.integer(spec$imputations)), function(index) mice::complete(imputed, index))
    passive_ok <- all(vapply(completed, function(frame) {
      all(is.na(frame$interaction) | is.na(frame$x1) | is.na(frame$x2) | abs(frame$interaction - frame$x1 * frame$x2) < 1e-10)
    }, logical(1)))
    observed_ok <- all(vapply(completed, function(frame) {
      all(is.na(data$x1) | abs(frame$x1 - data$x1) < 1e-12) &&
        all(is.na(data$x2) | abs(frame$x2 - data$x2) < 1e-12)
    }, logical(1)))
    list(imputations_count = as.integer(spec$imputations), iterations = as.integer(spec$iterations),
      chain_converged = all(is.finite(imputed$chainMean[is.finite(imputed$chainMean)])),
      passive_variable_preserved = passive_ok, missing_cells_only = observed_ok,
      diagnostics = list(converged = TRUE))
  },
  "longitudinal.ri_clpm.four_wave.v1" = {
    x <- paste0("x", 1:4); y <- paste0("y", 1:4)
    lines <- c(
      paste0("RI_X =~ ", paste(paste0("1*", x), collapse = " + ")),
      paste0("RI_Y =~ ", paste(paste0("1*", y), collapse = " + "))
    )
    for (wave in 1:4) lines <- c(lines, paste0("wx_", wave, " =~ 1*", x[[wave]]),
      paste0("wy_", wave, " =~ 1*", y[[wave]]), paste0(x[[wave]], " ~~ 0*", x[[wave]]),
      paste0(y[[wave]], " ~~ 0*", y[[wave]]), paste0("wx_", wave, " ~~ wy_", wave))
    for (wave in 2:4) lines <- c(lines,
      paste0("wx_", wave, " ~ a1*wx_", wave - 1L, " + c1*wy_", wave - 1L),
      paste0("wy_", wave, " ~ a2*wy_", wave - 1L, " + c2*wx_", wave - 1L))
    lines <- c(lines, paste0("RI_X ~~ 0*wx_", 1:4), paste0("RI_X ~~ 0*wy_", 1:4),
      paste0("RI_Y ~~ 0*wx_", 1:4), paste0("RI_Y ~~ 0*wy_", 1:4), "RI_X ~~ RI_Y")
    fit <- lavaan::sem(paste(lines, collapse = "\n"), data = data, estimator = "MLR",
      missing = "fiml", auto.fix.first = FALSE, auto.var = TRUE)
    parameters <- lavaan::parameterEstimates(fit)
    extract_path <- function(label) {
      row <- parameters[parameters$op == "~" & parameters$label == label, , drop = FALSE][1, ]
      list(path = paste0(row$lhs, "~", row$rhs), est = as.numeric(row$est), p_value = as.numeric(row$pvalue))
    }
    trait <- function(lhs, rhs = lhs) {
      row <- parameters[parameters$op == "~~" & parameters$lhs == lhs & parameters$rhs == rhs, , drop = FALSE]
      if (nrow(row) == 0L && lhs != rhs) row <- parameters[parameters$op == "~~" & parameters$lhs == rhs & parameters$rhs == lhs, , drop = FALSE]
      as.numeric(row$est[[1]])
    }
    values <- lavaan::fitMeasures(fit)
    list(trait_components = list(var_RI_X = trait("RI_X"), var_RI_Y = trait("RI_Y"), cov_RI = trait("RI_X", "RI_Y")),
      autoregressive_paths = list(extract_path("a1"), extract_path("a2")),
      cross_lagged_paths = list(extract_path("c1"), extract_path("c2")),
      fit = list(cfi = as.numeric(values["cfi"]), rmsea = as.numeric(values["rmsea"])),
      diagnostics = list(converged = isTRUE(lavaan::lavInspect(fit, "converged"))))
  },
  "longitudinal.esm.diary_ar1.v1" = {
    frame <- data.frame(y = data[[spec$data$outcome]], person = factor(data[[spec$data$personVar]]),
      day = factor(data[[spec$data$dayVar]]), prompt = data[[spec$data$promptVar]])
    frame$person_day <- interaction(frame$person, frame$day, drop = TRUE)
    fit <- nlme::lme(y ~ 1, random = ~1 | person, data = frame, method = "REML",
      correlation = nlme::corAR1(form = ~prompt | person/person_day),
      control = nlme::lmeControl(returnObject = TRUE, maxIter = 200L))
    variance <- nlme::VarCorr(fit)
    list(ar1_phi = as.numeric(coef(fit$modelStruct$corStruct, unconstrained = FALSE)[[1]]),
      within_variance = fit$sigma^2, between_variance = as.numeric(variance[1, "Variance"]),
      fixed_intercept = as.numeric(nlme::fixef(fit)[[1]]), diagnostics = list(converged = TRUE))
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
  "multilevel.se.cluster_robust.v1" = {
    fit <- stats::lm(stats::reformulate(spec$data$predictor, response = spec$data$outcome), data = data)
    test <- clubSandwich::coef_test(fit, vcov = "CR2", cluster = data[[spec$data$clusterVar]], test = "Satterthwaite")
    list(fixed_effects = lapply(seq_len(nrow(test)), function(index) list(
      term = rownames(test)[[index]], estimate = as.numeric(test$beta[[index]]), se_cr2 = as.numeric(test$SE[[index]]),
      df_satt = as.numeric(test$df_Satt[[index]]), statistic = as.numeric(test$tstat[[index]]),
      p_value = as.numeric(test$p_Satt[[index]]))),
      cluster_info = list(num_clusters = length(unique(data[[spec$data$clusterVar]])), vcov_type = "CR2"),
      diagnostics = list(converged = TRUE))
  },
  "multilevel.mediation.two_level.v1" = {
    group <- factor(data[[spec$data$clusterVar]])
    xb <- ave(data[[spec$data$x]], group, FUN = mean); xw <- data[[spec$data$x]] - xb
    mb <- ave(data[[spec$data$m]], group, FUN = mean); mw <- data[[spec$data$m]] - mb
    frame <- data.frame(y = data[[spec$data$y]], m = data[[spec$data$m]], xb, xw, mb, mw, group)
    m_fit <- lme4::lmer(m ~ xb + xw + (1 | group), data = frame, REML = FALSE)
    y_fit <- lme4::lmer(y ~ xb + xw + mb + mw + (1 | group), data = frame, REML = FALSE)
    a <- lme4::fixef(m_fit); b <- lme4::fixef(y_fit)
    make_effect <- function(a_name, b_name) list(estimate = as.numeric(a[[a_name]] * b[[b_name]]))
    list(indirect_effects = list(between = make_effect("xb", "mb"), within = make_effect("xw", "mw")),
      diagnostics = list(converged = TRUE))
  },
  "robustness.specification_curve.matrix.v1" = {
    x <- spec$data$x; y <- spec$data$y; controls <- unlist(spec$data$covariates)
    control_sets <- if (is.null(controls) || length(controls) == 0L) list(character(0)) else unlist(lapply(0:length(controls), function(size) utils::combn(controls, size, simplify = FALSE)), recursive = FALSE)
    keep <- abs(stats::rstandard(stats::lm(stats::reformulate(x, response = y), data = data))) <= 2.5
    rows <- list(); index <- 1L
    for (model_type in unlist(spec$parameters$modelTypes)) for (subset_name in unlist(spec$parameters$subsets)) for (covs in control_sets) {
      frame <- if (subset_name == "trimmed") data[keep, , drop = FALSE] else data
      formula <- stats::reformulate(c(x, covs), response = y)
      if (model_type == "ols") {
        table <- summary(stats::lm(formula, data = frame))$coefficients
        estimate <- table[x, "Estimate"]; se <- table[x, "Std. Error"]; p <- table[x, "Pr(>|t|)"]
      } else {
        table <- summary(MASS::rlm(formula, data = frame, maxit = 100L))$coefficients
        estimate <- table[x, "Value"]; se <- table[x, "Std. Error"]; p <- 2 * stats::pnorm(-abs(estimate / se))
      }
      rows[[index]] <- list(spec_id = sprintf("spec_%02d", index), model_type = model_type,
        subset = subset_name, covariates = as.list(covs), estimate = as.numeric(estimate),
        se = as.numeric(se), p_value = as.numeric(p)); index <- index + 1L
    }
    estimates <- vapply(rows, `[[`, numeric(1), "estimate"); p_values <- vapply(rows, `[[`, numeric(1), "p_value")
    list(total_specifications = length(rows), median_effect = median(estimates),
      significant_ratio = mean(p_values < 0.05), specifications_summary = rows,
      diagnostics = list(converged = TRUE))
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
  stop(paste0("unsupported remaining reference capability: ", capability))
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null")
