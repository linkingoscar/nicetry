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
dsem_inverse_wishart <- function(df, scale) {
  solve(rWishart(1L, df, solve(scale))[, , 1L])
}

dsem_safe_solve <- function(matrix) {
  solve(matrix + diag(1e-10, nrow(matrix)))
}

dsem_multivariate_normal <- function(mean, covariance) {
  drop(mean + t(chol(covariance)) %*% rnorm(length(mean)))
}

dsem_prepare_equations <- function(data, spec) {
  subject <- spec$subjectVariableId
  time <- spec$timeVariableId
  x <- spec$predictorVariableId
  y <- spec$outcomeVariableId
  counts <- table(data[[subject]])
  if (min(counts) < 20L) stop("DSEM_REQUIRES_AT_LEAST_20_OCCASIONS_PER_PERSON")
  if (length(counts) < 10L) stop("DSEM_REQUIRES_AT_LEAST_10_PERSONS")
  person <- as.character(data[[subject]])
  x_mean <- ave(data[[x]], person, FUN = mean)
  y_mean <- ave(data[[y]], person, FUN = mean)
  data$x_dsem_within <- data[[x]] - x_mean
  data$y_dsem_within <- data[[y]] - y_mean
  data$x_dsem_lag <- ave(data$x_dsem_within, person, FUN = function(values) {
    c(NA_real_, head(values, -1L))
  })
  data$y_dsem_lag <- ave(data$y_dsem_within, person, FUN = function(values) {
    c(NA_real_, head(values, -1L))
  })
  time_gap <- ave(data[[time]], person, FUN = function(values) {
    c(NA_real_, diff(values))
  })
  if (!is.null(spec$expectedTimeInterval)) {
    tolerance <- if (is.null(spec$timeIntervalTolerance)) 0 else spec$timeIntervalTolerance
    valid_gap <- abs(time_gap - spec$expectedTimeInterval) <= tolerance
    data$x_dsem_lag[!valid_gap] <- NA_real_
    data$y_dsem_lag[!valid_gap] <- NA_real_
  } else {
    finite_gaps <- time_gap[is.finite(time_gap)]
    if (length(unique(round(finite_gaps, 8))) > 1L) {
      stop("DSEM_IRREGULAR_INTERVAL_REQUIRES_EXPECTED_INTERVAL_AND_TOLERANCE")
    }
  }
  time_origin <- switch(
    spec$timeOriginStrategy,
    sample_mean = mean(data[[time]]),
    first_observed = min(data[[time]]),
    custom = spec$customTimeOrigin
  )
  data$time_dsem_centered <- data[[time]] - time_origin
  complete <- complete.cases(data[, c(
    "x_dsem_within",
    "y_dsem_within",
    "x_dsem_lag",
    "y_dsem_lag",
    "time_dsem_centered"
  )])
  data <- data[complete, , drop = FALSE]
  person <- as.character(data[[subject]])
  fixed_names <- c("intercept", "own_lag", "cross_lag")
  design_y <- cbind(1, data$y_dsem_lag, data$x_dsem_lag)
  design_x <- cbind(1, data$x_dsem_lag, data$y_dsem_lag)
  if (isTRUE(spec$includeLinearTime)) {
    design_y <- cbind(design_y, data$time_dsem_centered)
    design_x <- cbind(design_x, data$time_dsem_centered)
    fixed_names <- c(fixed_names, "linear_time")
  }
  if (isTRUE(spec$includeQuadraticTime)) {
    design_y <- cbind(design_y, data$time_dsem_centered^2)
    design_x <- cbind(design_x, data$time_dsem_centered^2)
    fixed_names <- c(fixed_names, "quadratic_time")
  }
  random_columns <- if (isTRUE(spec$dsem$randomDynamicSlopes)) {
    seq_len(3L)
  } else {
    1L
  }
  ids <- unique(person)
  split_rows <- split(seq_len(nrow(data)), factor(person, levels = ids))
  make_equation <- function(outcome, design) {
    lapply(split_rows, function(rows) {
      list(
        y = outcome[rows],
        x = design[rows, , drop = FALSE],
        z = design[rows, random_columns, drop = FALSE]
      )
    })
  }
  list(
    yEquation = make_equation(data$y_dsem_within, design_y),
    xEquation = make_equation(data$x_dsem_within, design_x),
    fixedNames = fixed_names,
    randomNames = fixed_names[random_columns],
    personIds = ids,
    sampleSize = nrow(data),
    timeOrigin = time_origin,
    xMeans = tapply(x_mean[complete], person, unique),
    yMeans = tapply(y_mean[complete], person, unique),
    data = data,
    designY = design_y,
    designX = design_x
  )
}

dsem_gibbs_equation <- function(groups, settings, chain_seed) {
  set.seed(chain_seed)
  group_count <- length(groups)
  fixed_count <- ncol(groups[[1]]$x)
  random_count <- ncol(groups[[1]]$z)
  iterations <- as.integer(settings$iterations)
  warmup <- as.integer(settings$warmup)
  thin <- as.integer(settings$thin)
  retained <- floor((iterations - warmup) / thin)
  beta <- rep(0, fixed_count)
  random_effects <- matrix(0, nrow = group_count, ncol = random_count)
  random_covariance <- diag(settings$priorScale^2, random_count)
  residual_variance <- rep(1, group_count)
  beta_draws <- matrix(NA_real_, nrow = retained, ncol = fixed_count)
  random_sd_draws <- matrix(NA_real_, nrow = retained, ncol = random_count)
  residual_draws <- numeric(retained)
  residual_between_sd_draws <- numeric(retained)
  prior_precision <- diag(1 / settings$priorMeanSd^2, fixed_count)
  prior_df <- random_count + 2L
  prior_scale <- diag(settings$priorScale^2, random_count)
  stored <- 0L
  for (iteration in seq_len(iterations)) {
    random_precision <- dsem_safe_solve(random_covariance)
    for (group_index in seq_len(group_count)) {
      group <- groups[[group_index]]
      covariance <- dsem_safe_solve(
        random_precision + crossprod(group$z) / residual_variance[[group_index]]
      )
      mean <- covariance %*% (
        crossprod(group$z, group$y - group$x %*% beta) /
          residual_variance[[group_index]]
      )
      random_effects[group_index, ] <- dsem_multivariate_normal(mean, covariance)
    }
    beta_precision <- prior_precision
    beta_score <- rep(0, fixed_count)
    for (group_index in seq_len(group_count)) {
      group <- groups[[group_index]]
      adjusted <- group$y - group$z %*% random_effects[group_index, ]
      beta_precision <- beta_precision +
        crossprod(group$x) / residual_variance[[group_index]]
      beta_score <- beta_score +
        drop(crossprod(group$x, adjusted)) / residual_variance[[group_index]]
    }
    beta_covariance <- dsem_safe_solve(beta_precision)
    beta <- dsem_multivariate_normal(beta_covariance %*% beta_score, beta_covariance)
    covariance_scale <- prior_scale + crossprod(random_effects)
    random_covariance <- dsem_inverse_wishart(
      prior_df + group_count,
      covariance_scale
    )
    for (group_index in seq_len(group_count)) {
      group <- groups[[group_index]]
      residual <- group$y -
        group$x %*% beta -
        group$z %*% random_effects[group_index, ]
      shape <- 2 + length(group$y) / 2
      rate <- settings$priorScale^2 + sum(residual^2) / 2
      residual_variance[[group_index]] <- 1 / rgamma(1L, shape = shape, rate = rate)
    }
    if (
      iteration > warmup &&
      (iteration - warmup) %% thin == 0L
    ) {
      stored <- stored + 1L
      beta_draws[stored, ] <- beta
      random_sd_draws[stored, ] <- sqrt(diag(random_covariance))
      residual_draws[[stored]] <- mean(residual_variance)
      residual_between_sd_draws[[stored]] <- sd(sqrt(residual_variance))
    }
  }
  list(
    beta = beta_draws,
    randomSd = random_sd_draws,
    residualVariance = residual_draws,
    residualBetweenSd = residual_between_sd_draws
  )
}

dsem_bind_parameter_chains <- function(chain_results, field, column) {
  do.call(rbind, lapply(chain_results, function(chain) {
    values <- chain[[field]]
    selected <- if (is.null(dim(values))) values else values[, column]
    matrix(selected, nrow = 1L)
  }))
}

dsem_bayesian_r2 <- function(groups, beta, random_sd) {
  outcomes <- numeric(0)
  predictions <- numeric(0)
  for (group in groups) {
    outcomes <- c(outcomes, group$y)
    predictions <- c(predictions, drop(group$x %*% beta))
  }
  explained <- var(predictions) + sum(random_sd^2)
  ensure_finite(explained / (explained + var(outcomes - predictions)))
}

dsem_series_statistic <- function(groups, statistic) {
  values <- unlist(lapply(groups, function(group) group$y), use.names = FALSE)
  if (identical(statistic, "mean")) return(mean(values))
  if (identical(statistic, "sd")) return(sd(values))
  correlations <- vapply(groups, function(group) {
    if (length(group$y) < 3L) return(NA_real_)
    suppressWarnings(cor(head(group$y, -1L), tail(group$y, -1L)))
  }, numeric(1))
  mean(correlations[is.finite(correlations)])
}

dsem_predictive_summary <- function(
  replicated,
  observed,
  equation,
  statistic,
  predictive = TRUE
) {
  list(
    equation = equation,
    statistic = statistic,
    observed = ensure_finite(observed),
    replicatedMedian = ensure_finite(unname(quantile(replicated, 0.5))),
    replicatedLower = ensure_finite(unname(quantile(replicated, 0.025))),
    replicatedUpper = ensure_finite(unname(quantile(replicated, 0.975))),
    confidenceLevelSource = "method_definition",
    bayesianPValue = if (predictive) {
      ensure_finite(mean(replicated >= observed))
    } else {
      NULL
    },
    observedWithinInterval = if (!predictive) {
      observed >= unname(quantile(replicated, 0.025)) &&
        observed <= unname(quantile(replicated, 0.975))
    } else {
      NULL
    }
  )
}

dsem_simulate_groups <- function(groups, beta, random_sd, residual_variance) {
  lapply(groups, function(group) {
    random_effect <- rnorm(ncol(group$z), 0, pmax(random_sd, 1e-8))
    list(
      y = drop(
        group$x %*% beta +
          group$z %*% random_effect +
          rnorm(length(group$y), 0, sqrt(max(residual_variance, 1e-8)))
      )
    )
  })
}

dsem_posterior_predictive_checks <- function(
  groups,
  chains,
  settings,
  equation,
  seed_offset
) {
  beta <- do.call(rbind, lapply(chains, function(chain) chain$beta))
  random_sd <- do.call(rbind, lapply(chains, function(chain) chain$randomSd))
  residual_variance <- unlist(lapply(chains, function(chain) chain$residualVariance))
  replications <- min(as.integer(settings$predictiveReplications), nrow(beta))
  selected <- unique(round(seq(1, nrow(beta), length.out = replications)))
  set.seed(researchpath_seed(settings$seed, seed_offset))
  statistics <- c("mean", "sd", "withinLag1")
  replicated <- lapply(statistics, function(statistic) numeric(length(selected)))
  for (draw_index in seq_along(selected)) {
    row <- selected[[draw_index]]
    generated <- dsem_simulate_groups(
      groups,
      beta[row, ],
      random_sd[row, ],
      residual_variance[[row]]
    )
    for (statistic_index in seq_along(statistics)) {
      replicated[[statistic_index]][[draw_index]] <- dsem_series_statistic(
        generated,
        statistics[[statistic_index]]
      )
    }
  }
  lapply(seq_along(statistics), function(index) {
    dsem_predictive_summary(
      replicated[[index]],
      dsem_series_statistic(groups, statistics[[index]]),
      equation,
      statistics[[index]],
      predictive = TRUE
    )
  })
}

dsem_prior_predictive_checks <- function(groups, settings, equation, seed_offset) {
  replications <- as.integer(settings$predictiveReplications)
  fixed_count <- ncol(groups[[1]]$x)
  random_count <- ncol(groups[[1]]$z)
  statistics <- c("mean", "sd", "withinLag1")
  replicated <- lapply(statistics, function(statistic) numeric(replications))
  set.seed(researchpath_seed(settings$seed, seed_offset))
  for (replication in seq_len(replications)) {
    beta <- rnorm(fixed_count, 0, settings$priorMeanSd)
    random_sd <- abs(rt(random_count, df = 4)) * settings$priorScale
    residual_variance <- 1 / rgamma(
      1L,
      shape = 2,
      rate = settings$priorScale^2
    )
    generated <- dsem_simulate_groups(
      groups,
      beta,
      random_sd,
      residual_variance
    )
    for (statistic_index in seq_along(statistics)) {
      replicated[[statistic_index]][[replication]] <- dsem_series_statistic(
        generated,
        statistics[[statistic_index]]
      )
    }
  }
  lapply(seq_along(statistics), function(index) {
    dsem_predictive_summary(
      replicated[[index]],
      dsem_series_statistic(groups, statistics[[index]]),
      equation,
      statistics[[index]],
      predictive = FALSE
    )
  })
}

dsem_plot_parameter <- function(chains, id, label, settings) {
  draw_count <- ncol(chains)
  selected <- unique(round(seq(
    1,
    draw_count,
    length.out = min(draw_count, as.integer(settings$plotDrawsPerChain))
  )))
  list(
    id = id,
    label = label,
    chains = lapply(seq_len(nrow(chains)), function(chain) {
      list(
        chain = chain,
        iterations = as.list(
          as.integer(settings$warmup + selected * settings$thin)
        ),
        values = as.list(vapply(
          chains[chain, selected],
          ensure_finite,
          numeric(1)
        ))
      )
    })
  )
}

dsem_weighted_quantile <- function(values, weights, probability) {
  ordering <- order(values)
  values <- values[ordering]
  weights <- weights[ordering] / sum(weights)
  values[[which(cumsum(weights) >= probability)[[1]]]]
}

dsem_prior_sensitivity_equation <- function(
  chains,
  prefix,
  settings,
  confidence_level
) {
  beta <- do.call(rbind, lapply(chains, function(chain) chain$beta))
  core_indices <- c(2L, 3L)
  baseline_sd <- settings$priorMeanSd
  alpha <- 1 - confidence_level
  scenarios <- unique(pmax(0.01, pmin(10, c(baseline_sd / 2, baseline_sd * 2))))
  lapply(scenarios, function(candidate_sd) {
    log_weights <- rowSums(
      dnorm(beta, 0, candidate_sd, log = TRUE) -
        dnorm(beta, 0, baseline_sd, log = TRUE)
    )
    log_weights <- log_weights - max(log_weights)
    weights <- exp(log_weights)
    weights <- weights / sum(weights)
    effects <- lapply(core_indices, function(index) {
      values <- beta[, index]
      baseline_lower <- unname(quantile(values, alpha / 2))
      baseline_upper <- unname(quantile(values, 1 - alpha / 2))
      estimate <- sum(values * weights)
      lower <- dsem_weighted_quantile(values, weights, alpha / 2)
      upper <- dsem_weighted_quantile(values, weights, 1 - alpha / 2)
      list(
        id = paste0(
          prefix,
          "_",
          if (index == 2L) "own_lag" else "cross_lag"
        ),
        estimate = ensure_finite(estimate),
        lower = ensure_finite(lower),
        upper = ensure_finite(upper),
        absoluteChange = ensure_finite(estimate - mean(values)),
        inferenceChanged = (baseline_lower > 0 || baseline_upper < 0) !=
          (lower > 0 || upper < 0)
      )
    })
    list(
      priorMeanSd = candidate_sd,
      reweightingEffectiveSampleSize = ensure_finite(1 / sum(weights^2)),
      effects = effects
    )
  })
}

dsem_prior_sensitivity <- function(
  chains_y,
  chains_x,
  settings,
  confidence_level
) {
  if (!isTRUE(settings$runPriorSensitivity)) return(NULL)
  y <- dsem_prior_sensitivity_equation(
    chains_y,
    "y",
    settings,
    confidence_level
  )
  x <- dsem_prior_sensitivity_equation(
    chains_x,
    "x",
    settings,
    confidence_level
  )
  list(
    method = paste0(
      "Joint importance reweighting of fixed-effect draws under Normal priors ",
      "with 0.5× and 2× baseline SD; other priors held fixed."
    ),
    scenarios = lapply(seq_along(y), function(index) {
      list(
        scenario = if (y[[index]]$priorMeanSd < settings$priorMeanSd) {
          "narrower_fixed_effect_prior"
        } else {
          "wider_fixed_effect_prior"
        },
        priorMeanSd = y[[index]]$priorMeanSd,
        reweightingEffectiveSampleSize = min(
          y[[index]]$reweightingEffectiveSampleSize,
          x[[index]]$reweightingEffectiveSampleSize
        ),
        effects = c(y[[index]]$effects, x[[index]]$effects)
      )
    })
  )
}

fit_diary_bayesian_dsem <- function(data, spec, label_for, confidence_level) {
  prepared <- dsem_prepare_equations(data, spec)
  settings <- spec$dsem
  if (is.null(settings$plotDrawsPerChain)) settings$plotDrawsPerChain <- 300L
  if (is.null(settings$predictiveReplications)) settings$predictiveReplications <- 200L
  if (is.null(settings$runPriorSensitivity)) settings$runPriorSensitivity <- TRUE
  chains_y <- lapply(seq_len(settings$chains), function(chain) {
    dsem_gibbs_equation(
      prepared$yEquation,
      settings,
      researchpath_seed(settings$seed, chain * 1009L)
    )
  })
  chains_x <- lapply(seq_len(settings$chains), function(chain) {
    dsem_gibbs_equation(
      prepared$xEquation,
      settings,
      researchpath_seed(settings$seed, chain * 2003L)
    )
  })
  summarize_equation <- function(chains, prefix, own_label, cross_label) {
    labels <- c(
      "动态方程截距",
      own_label,
      cross_label,
      if ("linear_time" %in% prepared$fixedNames) "线性时间趋势",
      if ("quadratic_time" %in% prepared$fixedNames) "二次时间趋势"
    )
    rows <- lapply(seq_along(prepared$fixedNames), function(index) {
      dsem_summary_row(
        dsem_bind_parameter_chains(chains, "beta", index),
        paste0(prefix, "_", prepared$fixedNames[[index]]),
        labels[[index]],
        confidence_level
      )
    })
    random_rows <- lapply(seq_along(prepared$randomNames), function(index) {
      dsem_summary_row(
        dsem_bind_parameter_chains(chains, "randomSd", index),
        paste0(prefix, "_random_sd_", prepared$randomNames[[index]]),
        paste0(labels[[match(prepared$randomNames[[index]], prepared$fixedNames)]], "的被试间 SD"),
        confidence_level
      )
    })
    variance_rows <- list(
      dsem_summary_row(
        dsem_bind_parameter_chains(chains, "residualVariance", 1L),
        paste0(prefix, "_mean_residual_variance"),
        "平均被试内创新方差",
        confidence_level
      ),
      dsem_summary_row(
        dsem_bind_parameter_chains(chains, "residualBetweenSd", 1L),
        paste0(prefix, "_residual_sd_heterogeneity"),
        "被试间创新 SD 异质性",
        confidence_level
      )
    )
    c(rows, random_rows, variance_rows)
  }
  effects <- c(
    summarize_equation(
      chains_y,
      "y",
      "Yₜ₋₁→Yₜ 自回归",
      "Xₜ₋₁→Yₜ 交叉滞后"
    ),
    summarize_equation(
      chains_x,
      "x",
      "Xₜ₋₁→Xₜ 自回归",
      "Yₜ₋₁→Xₜ 交叉滞后"
    )
  )
  max_rhat <- max(vapply(effects, function(row) row$rHat, numeric(1)), na.rm = TRUE)
  min_bulk_ess <- min(vapply(
    effects,
    function(row) row$bulkEffectiveSampleSize,
    numeric(1)
  ), na.rm = TRUE)
  min_tail_ess <- min(vapply(
    effects,
    function(row) row$tailEffectiveSampleSize,
    numeric(1)
  ), na.rm = TRUE)
  min_ess <- min(min_bulk_ess, min_tail_ess)
  retained_per_chain <- floor((settings$iterations - settings$warmup) / settings$thin)
  ess_threshold <- min(
    400,
    max(100, settings$chains * retained_per_chain / 5)
  )
  y_ar <- Filter(function(row) identical(row$id, "y_own_lag"), effects)[[1]]
  x_ar <- Filter(function(row) identical(row$id, "x_own_lag"), effects)[[1]]
  stationarity <- list(
    yAutoregressiveWithinUnitInterval = y_ar$lower > -1 && y_ar$upper < 1,
    xAutoregressiveWithinUnitInterval = x_ar$lower > -1 && x_ar$upper < 1
  )
  valid <- max_rhat <= 1.01 &&
    min_ess >= ess_threshold &&
    all(unlist(stationarity))
  diagnostics <- list()
  if (max_rhat > 1.01) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "DSEM_RHAT_FAILED",
      severity = "warning",
      message = "至少一个后验参数的 R-hat 大于 1.01。"
    )
  }
  if (min_ess < ess_threshold) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "DSEM_ESS_FAILED",
      severity = "warning",
      message = "至少一个后验参数的有效样本量低于预设门槛。"
    )
  }
  if (!all(unlist(stationarity))) {
    diagnostics[[length(diagnostics) + 1L]] <- list(
      code = "DSEM_STATIONARITY_FAILED",
      severity = "warning",
      message = "至少一个自回归参数的可信区间越过 ±1，动态平稳性不足。"
    )
  }
  beta_y <- colMeans(do.call(rbind, lapply(chains_y, function(chain) chain$beta)))
  beta_x <- colMeans(do.call(rbind, lapply(chains_x, function(chain) chain$beta)))
  random_sd_y <- colMeans(do.call(rbind, lapply(chains_y, function(chain) chain$randomSd)))
  random_sd_x <- colMeans(do.call(rbind, lapply(chains_x, function(chain) chain$randomSd)))
  posterior_checks <- c(
    dsem_posterior_predictive_checks(
      prepared$yEquation,
      chains_y,
      settings,
      "Y",
      3001L
    ),
    dsem_posterior_predictive_checks(
      prepared$xEquation,
      chains_x,
      settings,
      "X",
      4001L
    )
  )
  prior_checks <- c(
    dsem_prior_predictive_checks(
      prepared$yEquation,
      settings,
      "Y",
      5001L
    ),
    dsem_prior_predictive_checks(
      prepared$xEquation,
      settings,
      "X",
      6001L
    )
  )
  posterior_draws <- list(
    dsem_plot_parameter(
      dsem_bind_parameter_chains(chains_y, "beta", 2L),
      "y_own_lag",
      "Yₜ₋₁→Yₜ 自回归",
      settings
    ),
    dsem_plot_parameter(
      dsem_bind_parameter_chains(chains_y, "beta", 3L),
      "y_cross_lag",
      "Xₜ₋₁→Yₜ 交叉滞后",
      settings
    ),
    dsem_plot_parameter(
      dsem_bind_parameter_chains(chains_x, "beta", 2L),
      "x_own_lag",
      "Xₜ₋₁→Xₜ 自回归",
      settings
    ),
    dsem_plot_parameter(
      dsem_bind_parameter_chains(chains_x, "beta", 3L),
      "x_cross_lag",
      "Yₜ₋₁→Xₜ 交叉滞后",
      settings
    )
  )
  list(
    available = TRUE,
    analysisType = "bayesian_dsem",
    modelLabel = "观测变量 Bayesian DSEM（双向多层 VAR(1)）",
    sampleSize = prepared$sampleSize,
    personCount = length(prepared$personIds),
    observationsPerPerson = list(
      minimum = min(table(prepared$data[[spec$subjectVariableId]])),
      median = unname(median(table(prepared$data[[spec$subjectVariableId]]))),
      maximum = max(table(prepared$data[[spec$subjectVariableId]]))
    ),
    temporalEffect = "bidirectional_lagged",
    lagOrder = 1L,
    centering = "person_mean",
    timeOrigin = ensure_finite(prepared$timeOrigin),
    posteriorEffects = effects,
    mcmcDiagnostics = list(
      chains = settings$chains,
      iterationsPerChain = settings$iterations,
      warmupPerChain = settings$warmup,
      thin = settings$thin,
      retainedPerChain = retained_per_chain,
      maximumRHat = ensure_finite(max_rhat),
      minimumEffectiveSampleSize = ensure_finite(min_ess),
      minimumBulkEffectiveSampleSize = ensure_finite(min_bulk_ess),
      minimumTailEffectiveSampleSize = ensure_finite(min_tail_ess),
      effectiveSampleSizeThreshold = ensure_finite(ess_threshold),
      diagnosticMethod = paste0(
        "rank-normalized folded split R-hat; rank-normalized bulk ESS; ",
        "5%/95% tail ESS; MCSE for posterior means"
      ),
      stationarity = stationarity
    ),
    posteriorPredictive = list(
      yBayesianRSquared = dsem_bayesian_r2(
        prepared$yEquation,
        beta_y,
        random_sd_y
      ),
      xBayesianRSquared = dsem_bayesian_r2(
        prepared$xEquation,
        beta_x,
        random_sd_x
      ),
      checks = posterior_checks
    ),
    priorPredictive = list(
      method = paste0(
        "Prior predictive simulation from declared fixed-effect, random-effect ",
        "scale and innovation-variance priors."
      ),
      checks = prior_checks
    ),
    posteriorDraws = posterior_draws,
    priorSensitivity = dsem_prior_sensitivity(
      chains_y,
      chains_x,
      settings,
      confidence_level
    ),
    priorSpecification = list(
      fixedEffect = paste0("Normal(0, ", settings$priorMeanSd, "^2)"),
      randomEffectScale = settings$priorScale,
      residualVariance = paste0("Inverse-Gamma(2, ", settings$priorScale^2, ")"),
      seed = settings$seed
    ),
    diagnostics = diagnostics,
    validForInterpretation = valid,
    methodNotice = paste0(
      "本分析使用 ResearchPath 内置多链共轭 Gibbs 估计观测变量双向 Bayesian ",
      "多层 VAR(1)，包含随机截距、可选随机动态斜率和被试特异创新方差；",
      "模型不包含潜变量测量层、随机残差协方差、动态中介或高阶滞后。",
      "结果应解释为构念观测得分层面的时序动态关联，不应等同于完整 Mplus ",
      "潜变量 DSEM，也不能单独作为因果识别证据。"
    ),
    provenance = list(
      engine = "ResearchPath R conjugate Gibbs sampler",
      estimator = "Bayesian hierarchical dynamic path model",
      convergenceDiagnostic = paste0(
        "rank-normalized folded split R-hat, bulk/tail ESS and MCSE"
      ),
      reference = "Asparouhov, Hamaker, & Muthen (2018)",
      commercialSoftwareRequired = FALSE
    )
  )
}
