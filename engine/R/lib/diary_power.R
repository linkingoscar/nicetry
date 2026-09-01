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
diary_power_simulate_condition <- function(
  person_count,
  observations_per_person,
  power_spec,
  temporal_effect,
  random_slope,
  replication
) {
  set.seed(researchpath_seed(
    power_spec$seed,
    replication + person_count * 1009L + observations_per_person * 9176L
  ))
  subject <- factor(rep(seq_len(person_count), each = observations_per_person))
  time <- rep(seq_len(observations_per_person), times = person_count)
  between_x <- stats::rnorm(person_count, sd = power_spec$predictorBetweenSd)
  random_intercept <- stats::rnorm(person_count, sd = power_spec$randomInterceptSd)
  random_slope_value <- if (isTRUE(random_slope)) {
    stats::rnorm(person_count, sd = power_spec$randomSlopeSd)
  } else {
    rep(0, person_count)
  }
  within_x <- stats::rnorm(
    person_count * observations_per_person,
    sd = power_spec$predictorWithinSd
  )
  lagged_x <- ave(within_x, subject, FUN = function(values) {
    c(NA_real_, head(values, -1L))
  })
  target <- if (temporal_effect %in% c("lagged", "both")) lagged_x else within_x
  residual <- unlist(lapply(seq_len(person_count), function(index) {
    innovations <- stats::rnorm(
      observations_per_person,
      sd = power_spec$residualSd *
        sqrt(1 - power_spec$residualAr1^2)
    )
    stats::filter(
      innovations,
      filter = power_spec$residualAr1,
      method = "recursive",
      init = stats::rnorm(1L, sd = power_spec$residualSd)
    ) |>
      as.numeric()
  }), use.names = FALSE)
  outcome <- power_spec$betweenEffect * between_x[subject] +
    power_spec$withinEffect * ifelse(is.na(target), 0, target) +
    random_intercept[subject] +
    random_slope_value[subject] * ifelse(is.na(target), 0, target) +
    residual
  if (identical(temporal_effect, "both")) {
    outcome <- outcome + power_spec$withinEffect * within_x
  }
  data.frame(
    subject = subject,
    time = time,
    outcome = outcome,
    within_x = within_x,
    lagged_x = lagged_x,
    between_x = between_x[subject]
  )
}

diary_power_fit_replication <- function(
  person_count,
  observations_per_person,
  power_spec,
  temporal_effect,
  random_slope,
  replication
) {
  data <- diary_power_simulate_condition(
    person_count,
    observations_per_person,
    power_spec,
    temporal_effect,
    random_slope,
    replication
  )
  target_term <- if (temporal_effect %in% c("lagged", "both")) {
    "lagged_x"
  } else {
    "within_x"
  }
  fixed_terms <- if (identical(temporal_effect, "both")) {
    "within_x + lagged_x + between_x + time"
  } else {
    paste(target_term, "+ between_x + time")
  }
  random_terms <- if (isTRUE(random_slope)) {
    paste0("(1 + ", target_term, " | subject)")
  } else {
    "(1 | subject)"
  }
  formula <- stats::as.formula(paste("outcome ~", fixed_terms, "+", random_terms))
  fit <- tryCatch(
    suppressWarnings(lmerTest::lmer(
      formula,
      data = data,
      REML = FALSE,
      control = lme4::lmerControl(
        optimizer = "bobyqa",
        optCtrl = list(maxfun = 100000)
      )
    )),
    error = function(error) NULL
  )
  if (is.null(fit)) {
    return(list(converged = FALSE, singular = NULL))
  }
  coefficients <- summary(fit)$coefficients
  if (!target_term %in% rownames(coefficients)) {
    return(list(converged = FALSE, singular = lme4::isSingular(fit)))
  }
  estimate <- coefficients[target_term, "Estimate"]
  standard_error <- coefficients[target_term, "Std. Error"]
  degrees_freedom <- coefficients[target_term, "df"]
  statistic <- coefficients[target_term, "t value"]
  p_value <- coefficients[target_term, "Pr(>|t|)"]
  critical <- stats::qt(1 - power_spec$alpha / 2, df = degrees_freedom)
  list(
    converged = TRUE,
    singular = lme4::isSingular(fit),
    estimate = estimate,
    standardError = standard_error,
    statistic = statistic,
    pValue = p_value,
    lower = estimate - critical * standard_error,
    upper = estimate + critical * standard_error
  )
}

diary_power_analysis <- function(spec) {
  power_spec <- spec$powerAnalysis
  if (is.null(power_spec)) return(NULL)
  if (!requireNamespace("lme4", quietly = TRUE) ||
      !requireNamespace("lmerTest", quietly = TRUE)) {
    stop("DIARY_POWER_REQUIRES_LME4_AND_LMERTEST")
  }
  person_counts <- as.integer(unlist(power_spec$personCounts))
  observations <- as.integer(unlist(power_spec$observationsPerPerson))
  conditions <- expand.grid(
    personCount = person_counts,
    observationsPerPerson = observations,
    KEEP.OUT.ATTRS = FALSE
  )
  conditions <- conditions[
    order(conditions$personCount, conditions$observationsPerPerson),
    ,
    drop = FALSE
  ]
  rows <- lapply(seq_len(nrow(conditions)), function(condition_index) {
    person_count <- conditions$personCount[[condition_index]]
    observation_count <- conditions$observationsPerPerson[[condition_index]]
    replications <- lapply(seq_len(as.integer(power_spec$replications)), function(index) {
      diary_power_fit_replication(
        person_count,
        observation_count,
        power_spec,
        spec$temporalEffect,
        isTRUE(spec$randomSlope),
        index
      )
    })
    converged <- Filter(function(result) isTRUE(result$converged), replications)
    estimates <- vapply(converged, function(result) result$estimate, numeric(1))
    standard_errors <- vapply(
      converged,
      function(result) result$standardError,
      numeric(1)
    )
    p_values <- vapply(converged, function(result) result$pValue, numeric(1))
    coverage <- vapply(converged, function(result) {
      result$lower <= power_spec$withinEffect &&
        result$upper >= power_spec$withinEffect
    }, logical(1))
    singular_count <- sum(vapply(replications, function(result) {
      isTRUE(result$singular)
    }, logical(1)))
    significant_count <- sum(p_values < power_spec$alpha)
    unconditional_power <- significant_count / length(replications)
    conditional_power <- if (length(p_values) == 0L) NULL else {
      significant_count / length(p_values)
    }
    coverage_rate <- if (length(coverage) == 0L) NULL else mean(coverage)
    list(
      personCount = person_count,
      observationsPerPerson = observation_count,
      totalObservations = person_count * observation_count,
      convergedReplications = length(converged),
      failedReplications = length(replications) - length(converged),
      singularReplications = singular_count,
      convergenceRate = length(converged) / length(replications),
      averageEstimate = if (length(estimates) == 0L) NULL else mean(estimates),
      bias = if (length(estimates) == 0L) NULL else {
        mean(estimates) - power_spec$withinEffect
      },
      empiricalStandardError = if (length(estimates) < 2L) NULL else {
        stats::sd(estimates)
      },
      averageStandardError = if (length(standard_errors) == 0L) NULL else {
        mean(standard_errors)
      },
      coverage = coverage_rate,
      coverageMcse = if (is.null(coverage_rate)) NULL else {
        sqrt(coverage_rate * (1 - coverage_rate) / length(coverage))
      },
      powerConditionalOnConvergence = conditional_power,
      power = unconditional_power,
      powerMcse = sqrt(
        unconditional_power * (1 - unconditional_power) / length(replications)
      )
    )
  })
  adequate <- Filter(function(row) {
    !is.null(row$power) &&
      row$power >= power_spec$targetPower &&
      row$convergenceRate >= 0.95
  }, rows)
  if (length(adequate) > 0L) {
    adequate <- adequate[order(
      vapply(adequate, function(row) row$totalObservations, numeric(1)),
      vapply(adequate, function(row) row$personCount, numeric(1))
    )]
  }
  target_term <- if (spec$temporalEffect %in% c("lagged", "both")) {
    "lagged within-person effect"
  } else {
    "contemporaneous within-person effect"
  }
  list(
    method = "Monte Carlo multilevel power analysis",
    targetParameter = target_term,
    targetPower = power_spec$targetPower,
    alpha = power_spec$alpha,
    replications = as.integer(power_spec$replications),
    seed = researchpath_seed(power_spec$seed),
    assumptions = list(
      temporalEffect = spec$temporalEffect,
      withinEffect = power_spec$withinEffect,
      betweenEffect = power_spec$betweenEffect,
      randomInterceptSd = power_spec$randomInterceptSd,
      randomSlopeSd = power_spec$randomSlopeSd,
      residualSd = power_spec$residualSd,
      predictorBetweenSd = power_spec$predictorBetweenSd,
      predictorWithinSd = power_spec$predictorWithinSd,
      residualAr1 = power_spec$residualAr1,
      randomSlope = isTRUE(spec$randomSlope)
    ),
    failureRule = "Failed fits remain in the denominator and count as no rejection.",
    results = rows,
    recommendation = if (length(adequate) == 0L) NULL else adequate[[1]],
    validForPlanning = all(vapply(rows, function(row) {
      row$convergenceRate >= 0.8 && !is.null(row$power)
    }, logical(1))),
    provenance = list(
      engine = "R lme4 + lmerTest Monte Carlo",
      lme4Version = as.character(utils::packageVersion("lme4")),
      lmerTestVersion = as.character(utils::packageVersion("lmerTest"))
    )
  )
}
