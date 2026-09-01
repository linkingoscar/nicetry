.this_dir <- tryCatch(dirname(sys.frame(1)$ofile), error = function(e) NULL)
if (is.null(.this_dir) || nchar(.this_dir) == 0) .this_dir <- "."
if (file.exists(file.path(.this_dir, "diary_utils.R"))) {
  source(file.path(.this_dir, "diary_utils.R"))
  source(file.path(.this_dir, "centering_utils.R"))
  source(file.path(.this_dir, "time_series_utils.R"))
}
diary_quality_evidence <- function(data, spec) {
  subject <- spec$subjectVariableId
  if (!subject %in% names(data)) stop("DIARY_SUBJECT_COLUMN_NOT_FOUND")
  valid_subject <- !is.na(data[[subject]]) & nzchar(as.character(data[[subject]]))
  subject_values <- as.character(data[[subject]][valid_subject])
  observed_counts <- table(subject_values)
  expected <- spec$expectedObservationsPerPerson
  rates <- if (is.null(expected)) {
    rep(NA_real_, length(observed_counts))
  } else {
    pmin(1, as.numeric(observed_counts) / as.numeric(expected))
  }
  names(rates) <- names(observed_counts)
  threshold <- if (is.null(spec$minimumComplianceRate)) 0 else spec$minimumComplianceRate
  low_ids <- if (is.null(expected) || threshold <= 0) {
    character(0)
  } else {
    names(rates)[rates < threshold]
  }

  latency_id <- spec$responseLatencyVariableId
  latency <- NULL
  valid_window <- rep(TRUE, nrow(data))
  if (!is.null(latency_id) && nzchar(latency_id)) {
    if (!latency_id %in% names(data)) stop("DIARY_RESPONSE_LATENCY_COLUMN_NOT_FOUND")
    latency <- suppressWarnings(as.numeric(data[[latency_id]]))
    valid_window <- is.finite(latency)
    if (!is.null(spec$minimumResponseLatency)) {
      valid_window <- valid_window & latency >= spec$minimumResponseLatency
    }
    if (!is.null(spec$maximumResponseLatency)) {
      valid_window <- valid_window & latency <= spec$maximumResponseLatency
    }
  }
  latency_finite <- if (is.null(latency)) numeric(0) else latency[is.finite(latency)]
  list(
    evidence = list(
      personCount = length(observed_counts),
      observedPromptRows = sum(observed_counts),
      expectedObservationsPerPerson = expected,
      overallComplianceRate = if (is.null(expected)) {
        NULL
      } else {
        ensure_finite(sum(observed_counts) / (length(observed_counts) * expected))
      },
      personCompliance = list(
        minimum = if (all(is.na(rates))) NULL else ensure_finite(min(rates, na.rm = TRUE)),
        median = if (all(is.na(rates))) NULL else ensure_finite(median(rates, na.rm = TRUE)),
        maximum = if (all(is.na(rates))) NULL else ensure_finite(max(rates, na.rm = TRUE)),
        belowThresholdCount = length(low_ids),
        threshold = threshold
      ),
      responseLatency = if (length(latency_finite) == 0L) {
        NULL
      } else {
        list(
          n = length(latency_finite),
          mean = ensure_finite(mean(latency_finite)),
          median = ensure_finite(median(latency_finite)),
          p95 = ensure_finite(unname(quantile(latency_finite, 0.95))),
          minimum = ensure_finite(min(latency_finite)),
          maximum = ensure_finite(max(latency_finite)),
          outsideWindowCount = sum(!valid_window)
        )
      },
      exclusionRules = list(
        excludeLowCompliance = isTRUE(spec$excludeLowCompliance),
        excludeOutOfWindow = isTRUE(spec$excludeOutOfWindow)
      )
    ),
    lowComplianceIds = low_ids,
    validWindow = valid_window
  )
}

diary_apply_quality_rules <- function(data, spec, quality) {
  keep <- rep(TRUE, nrow(data))
  if (isTRUE(spec$excludeLowCompliance) && length(quality$lowComplianceIds) > 0L) {
    keep <- keep & !as.character(data[[spec$subjectVariableId]]) %in% quality$lowComplianceIds
  }
  if (isTRUE(spec$excludeOutOfWindow)) keep <- keep & quality$validWindow
  data[keep, , drop = FALSE]
}

diary_temporal_design <- function(data, spec, centered) {
  subject <- spec$subjectVariableId
  time <- spec$timeVariableId
  temporal <- if (is.null(spec$temporalEffect)) "contemporaneous" else spec$temporalEffect
  lag_order <- if (is.null(spec$lagOrder)) 1L else as.integer(spec$lagOrder)
  within <- centered$within
  predictor_terms <- character(0)
  if (temporal %in% c("contemporaneous", "both")) predictor_terms <- c(predictor_terms, within)
  lagged_id <- NULL
  gap_id <- NULL
  if (temporal %in% c("lagged", "both")) {
    lagged_id <- paste0(within, "__lag", lag_order)
    gap_id <- paste0(time, "__gap", lag_order)
    data[[lagged_id]] <- ave(data[[within]], data[[subject]], FUN = function(values) {
      c(rep(NA_real_, lag_order), head(values, -lag_order))
    })
    data[[gap_id]] <- ave(data[[time]], data[[subject]], FUN = function(values) {
      values - c(rep(NA_real_, lag_order), head(values, -lag_order))
    })
    if (!is.null(spec$expectedTimeInterval)) {
      expected_gap <- spec$expectedTimeInterval * lag_order
      tolerance <- if (is.null(spec$timeIntervalTolerance)) 0 else spec$timeIntervalTolerance
      outside <- abs(data[[gap_id]] - expected_gap) > tolerance
      data[[lagged_id]][outside] <- NA_real_
    }
    predictor_terms <- c(predictor_terms, lagged_id)
  }

  origin_strategy <- if (is.null(spec$timeOriginStrategy)) {
    "sample_mean"
  } else {
    spec$timeOriginStrategy
  }
  origin_value <- switch(
    origin_strategy,
    sample_mean = mean(data[[time]], na.rm = TRUE),
    first_observed = min(data[[time]], na.rm = TRUE),
    custom = spec$customTimeOrigin,
    stop("DIARY_TIME_ORIGIN_STRATEGY_NOT_SUPPORTED")
  )
  if (is.null(origin_value) || !is.finite(origin_value)) {
    stop("DIARY_TIME_ORIGIN_NOT_FINITE")
  }
  time_centered <- paste0(time, "__centered")
  data[[time_centered]] <- data[[time]] - origin_value
  time_terms <- character(0)
  if (isTRUE(spec$includeLinearTime)) time_terms <- c(time_terms, time_centered)
  time_squared <- NULL
  if (isTRUE(spec$includeQuadraticTime)) {
    time_squared <- paste0(time, "__centered_sq")
    data[[time_squared]] <- data[[time_centered]]^2
    time_terms <- c(time_terms, time_squared)
  }

  interaction_terms <- character(0)
  interaction_formulas <- character(0)
  moderator <- spec$level2ModeratorVariableId
  moderator_protocol <- NULL
  if (!is.null(moderator) && nzchar(moderator)) {
    subject_values <- as.character(data[[subject]])
    person_moderator <- tapply(data[[moderator]], subject_values, function(values) {
      finite <- unique(values[is.finite(values)])
      if (length(finite) == 1L) finite[[1]] else NA_real_
    })
    if (any(!is.finite(person_moderator))) stop("LEVEL2_MODERATOR_VARIES_WITHIN_PERSON")
    moderator_grand_mean <- mean(person_moderator)
    moderator_centered <- paste0(moderator, "__grand_centered")
    data[[moderator_centered]] <- unname(
      person_moderator[subject_values] - moderator_grand_mean
    )
    moderator_protocol <- list(
      strategy = "CGM_person_equal",
      formula = paste0(moderator, "_i - mean_person(", moderator, ")"),
      grandMeanWeighting = "equal weight per person",
      reference = ensure_finite(moderator_grand_mean),
      centeredVariableId = moderator_centered
    )
    for (predictor in predictor_terms) {
      interaction <- paste0(predictor, "__x__", moderator_centered)
      data[[interaction]] <- data[[predictor]] * data[[moderator_centered]]
      interaction_terms <- c(interaction_terms, interaction)
      interaction_formulas <- c(
        interaction_formulas,
        paste0(interaction, " = ", predictor, " × ", moderator_centered)
      )
    }
    predictor_terms <- c(predictor_terms, moderator_centered, interaction_terms)
  }

  list(
    data = data,
    predictorTerms = predictor_terms,
    laggedPredictorId = lagged_id,
    timeGapId = gap_id,
    timeTerms = time_terms,
    interactionTerms = interaction_terms,
    interactionFormulas = interaction_formulas,
    moderatorProtocol = moderator_protocol,
    timeProtocol = list(
      originStrategy = origin_strategy,
      originValue = ensure_finite(origin_value),
      centeredVariableId = time_centered,
      linearTerm = time_centered,
      quadraticTerm = time_squared,
      observedMinimum = ensure_finite(min(data[[time]], na.rm = TRUE)),
      observedMaximum = ensure_finite(max(data[[time]], na.rm = TRUE))
    )
  )
}

diary_alpha_from_covariance <- function(covariance) {
  item_count <- ncol(covariance)
  total_variance <- sum(covariance)
  if (item_count < 2L || !is.finite(total_variance) || total_variance <= 0) return(NULL)
  ensure_finite(item_count / (item_count - 1) * (1 - sum(diag(covariance)) / total_variance))
}

diary_multilevel_reliability <- function(data, spec) {
  constructs <- spec$reliabilityConstructs
  if (is.null(constructs) || length(constructs) == 0L) return(list())
  subject <- spec$subjectVariableId
  lapply(constructs, function(construct) {
    item_ids <- unlist(construct$itemIds, use.names = FALSE)
    missing_columns <- setdiff(item_ids, names(data))
    if (length(missing_columns) > 0L) {
      stop(paste0("DIARY_RELIABILITY_COLUMNS_NOT_FOUND: ", paste(missing_columns, collapse = ", ")))
    }
    item_data <- data[, c(subject, item_ids), drop = FALSE]
    for (item in item_ids) item_data[[item]] <- suppressWarnings(as.numeric(item_data[[item]]))
    item_data <- item_data[complete.cases(item_data), , drop = FALSE]
    person_means <- aggregate(
      item_data[, item_ids, drop = FALSE],
      by = list(subject = item_data[[subject]]),
      FUN = mean
    )
    within <- item_data[, item_ids, drop = FALSE]
    for (item in item_ids) {
      within[[item]] <- within[[item]] -
        ave(within[[item]], item_data[[subject]], FUN = mean)
    }
    within_covariance <- cov(within)
    between_covariance <- cov(person_means[, item_ids, drop = FALSE])
    item_iccs <- vapply(item_ids, function(item) {
      fit <- lme4::lmer(
        reformulate(paste0("(1|", subject, ")"), response = item),
        data = item_data,
        REML = TRUE
      )
      variance <- as.data.frame(lme4::VarCorr(fit))
      between <- variance$vcov[variance$grp == subject & variance$var1 == "(Intercept)"][[1]]
      residual <- sigma(fit)^2
      between / (between + residual)
    }, numeric(1))
    list(
      label = construct$label,
      itemIds = as.list(item_ids),
      observationCount = nrow(item_data),
      personCount = nrow(person_means),
      withinAlpha = diary_alpha_from_covariance(within_covariance),
      betweenAlpha = diary_alpha_from_covariance(between_covariance),
      meanItemIcc = ensure_finite(mean(item_iccs)),
      itemIccs = lapply(seq_along(item_ids), function(index) {
        list(itemId = item_ids[[index]], icc = ensure_finite(item_iccs[[index]]))
      }),
      method = "Within-person centered covariance alpha and between-person mean covariance alpha"
    )
  })
}
