moderator_summary <- NULL
probes <- list()
jn_result <- NULL
jn_results <- list()
moderation_plots <- list()

process_representative_values <- function(values) {
  result <- as.numeric(quantile(
    values,
    probs = c(0.16, 0.50, 0.84),
    names = FALSE,
    type = 6
  ))
  names(result) <- c("percentile_16", "median", "percentile_84")
  result
}

build_johnson_neyman <- function(
  b1, b3, covariance, predictor_term, interaction_term, moderator_original,
  moderator_center, critical, confidence_level, is_glm_fit, standard_error_method
) {
  if (!researchpath_covariance_available(covariance)) {
    return(list(available = FALSE, reason = "HC3_UNAVAILABLE"))
  }
  v11 <- covariance[predictor_term, predictor_term]
  v13 <- covariance[predictor_term, interaction_term]
  v33 <- covariance[interaction_term, interaction_term]
  qa <- b3^2 - critical^2 * v33
  qb <- 2 * b1 * b3 - 2 * critical^2 * v13
  qc <- b1^2 - critical^2 * v11
  discriminant <- qb^2 - 4 * qa * qc
  roots_model <- numeric(0)
  if (is.finite(discriminant) && discriminant >= 0 && abs(qa) > 1e-12) {
    roots_model <- sort(c(
      (-qb - sqrt(discriminant)) / (2 * qa),
      (-qb + sqrt(discriminant)) / (2 * qa)
    ))
  } else if (abs(qa) <= 1e-12 && abs(qb) > 1e-12) {
    roots_model <- -qc / qb
  }
  roots_original <- roots_model + moderator_center
  observed_minimum <- min(moderator_original)
  observed_maximum <- max(moderator_original)
  observed_roots <- roots_original[
    roots_original >= observed_minimum & roots_original <= observed_maximum
  ]

  conditional_row <- function(original_value) {
    model_value <- original_value - moderator_center
    effect <- b1 + b3 * model_value
    variance <- v11 + 2 * model_value * v13 + model_value^2 * v33
    standard_error <- sqrt(max(variance, 0))
    statistic <- if (standard_error > 0) effect / standard_error else NA_real_
    p_value <- if (!is.finite(statistic)) {
      NA_real_
    } else if (is_glm_fit) {
      2 * pnorm(abs(statistic), lower.tail = FALSE)
    } else {
      2 * pt(abs(statistic), df = df.residual(fit), lower.tail = FALSE)
    }
    lower <- effect - critical * standard_error
    upper <- effect + critical * standard_error
    list(
      moderatorValue = finite_number(original_value),
      effect = finite_number(effect),
      standardError = finite_number(standard_error),
      statistic = finite_number(statistic),
      pValue = finite_number(p_value),
      lower = finite_number(lower),
      upper = finite_number(upper),
      significant = is.finite(lower) && is.finite(upper) && (lower > 0 || upper < 0)
    )
  }
  grid <- lapply(
    seq(observed_minimum, observed_maximum, length.out = 101L),
    conditional_row
  )
  breakpoints <- sort(unique(c(
    observed_minimum, observed_roots, observed_maximum
  )))
  regions <- lapply(seq_len(max(0L, length(breakpoints) - 1L)), function(index) {
    lower <- breakpoints[[index]]
    upper <- breakpoints[[index + 1L]]
    midpoint <- conditional_row((lower + upper) / 2)
    status <- if (!isTRUE(midpoint$significant)) {
      "not_significant"
    } else if (midpoint$effect > 0) {
      "positive"
    } else {
      "negative"
    }
    list(
      lower = finite_number(lower), upper = finite_number(upper),
      status = status, effectAtMidpoint = midpoint$effect
    )
  })
  result <- list(
    available = length(roots_original) > 0L,
    boundaries = as.list(vapply(roots_original, finite_number, numeric(1))),
    observedBoundaries = as.list(vapply(observed_roots, finite_number, numeric(1))),
    observedMinimum = finite_number(observed_minimum),
    observedMaximum = finite_number(observed_maximum),
    confidenceLevel = confidence_level,
    criticalValue = finite_number(critical),
    method = standard_error_method,
    grid = grid,
    regions = regions
  )
  if (length(roots_original) == 0L) {
    result$reason <- "条件效应置信区间在观测尺度上没有有限临界点"
  }
  if (length(roots_original) >= 1L) result$lower <- finite_number(roots_original[[1]])
  if (length(roots_original) >= 2L) result$upper <- finite_number(roots_original[[2]])
  result
}

if (!is.null(w_node)) {
  w_original <- original_values[[w_node$id]]
  w_mean <- mean(w_original)
  w_sd <- sd(w_original)
  representative_original <- process_representative_values(w_original)
  center <- if (is.null(centering_means[[w_node$id]])) 0 else centering_means[[w_node$id]]
  representative_model <- representative_original - center
  moderator_summary <- list(id = w_node$id, mean = w_mean, standardDeviation = w_sd, minimum = min(w_original), maximum = max(w_original))

  direct_moderation <- NULL
  for (mod in spec$moderations) {
    target <- edge_for_id(mod$targetEdgeId)
    if (identical(target$from, x_node$id) && identical(target$to, y_node$id)) {
      direct_moderation <- mod
      break
    }
  }
  primary_moderation <- if (!is.null(direct_moderation)) direct_moderation else if (length(spec$moderations) >= 1) spec$moderations[[1]] else NULL
  node_label <- function(node_id) {
    match <- Filter(function(node) identical(node$id, node_id), spec$nodes)
    if (length(match) == 1 && !is.null(match[[1]]$label)) match[[1]]$label else node_id
  }

  for (mod in spec$moderations) {
    target <- edge_for_id(mod$targetEdgeId)
    fit_name <- fit_key_by_outcome[[target$to]]
    if (is.null(fit_name)) {
      stop(sprintf("No fitted equation for moderated outcome %s", target$to))
    }
    fit <- fits[[fit_name]]

    if (!is.null(mod$secondaryModeratorNodeId)) {
      joint_estimate <- unname(coef(fit)[[mod$productTermId]])
      effects[[length(effects) + 1]] <- list(
        id = paste0("effect_", mod$id),
        type = "interaction",
        label = paste0(
          "interaction_", target$from, "_x_",
          mod$moderatorNodeId, "_x_", mod$secondaryModeratorNodeId
        ),
        estimate = joint_estimate
      )
      next
    }

    moderator_matches <- Filter(
      function(node) identical(node$id, mod$moderatorNodeId),
      spec$nodes
    )
    moderator_node <- moderator_matches[[1]]
    target_moderations <- Filter(
      function(item) identical(item$targetEdgeId, mod$targetEdgeId),
      spec$moderations
    )
    if (isTRUE(generic_process) && length(target_moderations) > 1L) {
      effects[[length(effects) + 1]] <- list(
        id = paste0("effect_", mod$id), type = "interaction",
        label = paste0("interaction_", target$from, "_x_", moderator_node$id),
        estimate = unname(coef(fit)[[mod$productTermId]])
      )
      next
    }
    moderator_original <- original_values[[moderator_node$id]]
    current_representative_original <-
      process_representative_values(moderator_original)
    current_center <- if (is.null(centering_means[[moderator_node$id]])) {
      0
    } else {
      centering_means[[moderator_node$id]]
    }
    current_representative_model <-
      current_representative_original - current_center

    covariance <- model_vcov(fit)
    b1 <- unname(coef(fit)[[target$from]])
    b3 <- unname(coef(fit)[[mod$productTermId]])
    is_glm_fit <- inherits(fit, "glm")
    critical <- if (is_glm_fit) qnorm(1 - alpha / 2) else qt(1 - alpha / 2, df = df.residual(fit))

    if (!template %in% c("model_2", "model_3")) {
      for (index in seq_along(current_representative_model)) {
        value <- current_representative_model[[index]]
        slope <- b1 + b3 * value
        variance <- covariance[target$from, target$from] + 2 * value * covariance[target$from, mod$productTermId] + value^2 * covariance[mod$productTermId, mod$productTermId]
        se <- sqrt(variance)
        statistic <- slope / se

        lbl <- if (length(spec$moderations) > 1) {
          paste0(target$from, "->", target$to, " (", names(current_representative_original)[[index]], ")")
        } else {
          names(current_representative_original)[[index]]
        }

        probes[[length(probes) + 1]] <- list(
          moderationId = mod$id,
          targetEdgeId = target$id,
          predictorLabel = node_label(target$from),
          moderatorLabel = node_label(mod$moderatorNodeId),
          label = lbl,
          moderatorValue = unname(current_representative_original[[index]]),
          effect = slope, standardError = se,
          statistic = statistic,
          pValue = if (is_glm_fit) 2 * pnorm(abs(statistic), lower.tail = FALSE) else 2 * pt(abs(statistic), df = df.residual(fit), lower.tail = FALSE),
          confidenceInterval = list(
            level = spec$estimation$confidenceLevel,
            lower = slope - critical * se,
            upper = slope + critical * se,
            method = researchpath_confidence_interval_method(
              covariance, is_glm_fit, spec$estimation$standardErrors
            )
          )
        )
      }
    }

    source_original <- original_values[[target$from]]
    source_center <- if (is.null(centering_means[[target$from]])) 0 else centering_means[[target$from]]
    source_values_original <- as.numeric(quantile(
      source_original,
      probs = c(0.16, 0.84),
      names = FALSE,
      type = 6
    ))
    base_prediction_row <- analysis_data[1, , drop = FALSE]
    for (column_name in names(base_prediction_row)) {
      base_prediction_row[[column_name]] <- mean(analysis_data[[column_name]])
    }
    plot_lines <- lapply(seq_along(current_representative_model), function(index) {
      prediction_data <- base_prediction_row[rep(1, 2), , drop = FALSE]
      prediction_data[[target$from]] <- source_values_original - source_center
      prediction_data[[mod$moderatorNodeId]] <-
        rep(current_representative_model[[index]], 2)
      for (linked_mod in spec$moderations) {
        linked_target <- edge_for_id(linked_mod$targetEdgeId)
        if (linked_mod$productTermId %in% names(prediction_data)) {
          if (!is.null(linked_mod$secondaryModeratorNodeId)) {
            prediction_data[[linked_mod$moderatorProductTermId]] <-
              prediction_data[[linked_mod$moderatorNodeId]] *
              prediction_data[[linked_mod$secondaryModeratorNodeId]]
            prediction_data[[linked_mod$productTermId]] <-
              prediction_data[[linked_target$from]] *
              prediction_data[[linked_mod$moderatorNodeId]] *
              prediction_data[[linked_mod$secondaryModeratorNodeId]]
          } else {
            prediction_data[[linked_mod$productTermId]] <-
              prediction_data[[linked_target$from]] *
              prediction_data[[linked_mod$moderatorNodeId]]
          }
        }
      }
      prediction_design <- model.matrix(delete.response(terms(fit)), prediction_data, contrasts.arg = fit$contrasts)
      linear_prediction <- as.numeric(prediction_design %*% coef(fit))
      prediction_standard_error <- sqrt(rowSums((prediction_design %*% covariance) * prediction_design))
      lower_link <- linear_prediction - critical * prediction_standard_error
      upper_link <- linear_prediction + critical * prediction_standard_error
      if (is_glm_fit) {
        predicted <- plogis(linear_prediction)
        prediction_lower <- plogis(lower_link)
        prediction_upper <- plogis(upper_link)
      } else {
        predicted <- linear_prediction
        prediction_lower <- lower_link
        prediction_upper <- upper_link
      }
      list(
        label = names(current_representative_original)[[index]],
        moderatorValue = unname(current_representative_original[[index]]),
        xValues = as.list(as.numeric(source_values_original)),
        predictedValues = as.list(predicted),
        confidenceLower = as.list(as.numeric(prediction_lower)),
        confidenceUpper = as.list(as.numeric(prediction_upper))
      )
    })
    moderation_plots[[length(moderation_plots) + 1]] <- list(
      id = paste0("plot_", mod$id),
      targetEdgeId = target$id,
      equationId = paste0("equation_", fit_name),
      predictorId = target$from,
      predictorLabel = node_label(target$from),
      outcomeId = target$to,
      outcomeLabel = node_label(target$to),
      moderatorId = mod$moderatorNodeId,
      moderatorLabel = node_label(mod$moderatorNodeId),
      outcomeScale = if (inherits(fit, "glm")) "probability" else "outcome",
      lines = plot_lines
    )

    standard_error_method <- researchpath_confidence_interval_method(
      covariance, is_glm_fit, spec$estimation$standardErrors
    )
    mod_jn <- build_johnson_neyman(
      b1, b3, covariance, target$from, mod$productTermId,
      moderator_original, current_center, critical,
      spec$estimation$confidenceLevel, is_glm_fit, standard_error_method
    )
    jn_results[[length(jn_results) + 1L]] <- list(
      moderationId = mod$id,
      targetEdgeId = target$id,
      predictorId = target$from,
      predictorLabel = node_label(target$from),
      moderatorId = mod$moderatorNodeId,
      moderatorLabel = node_label(mod$moderatorNodeId),
      result = mod_jn
    )

    if (
      !template %in% c("model_2", "model_3") &&
      identical(mod$id, primary_moderation$id)
    ) {
      jn_result <- mod_jn
    }

    effects[[length(effects) + 1]] <- list(
      id = paste0("effect_", mod$id), type = "interaction",
      label = paste0("interaction_", target$from, "_x_", moderator_node$id), estimate = b3
    )
  }
}

if (isTRUE(generic_process)) {
  moderation_target_ids <- unique(vapply(
    spec$moderations,
    function(item) item$targetEdgeId,
    character(1)
  ))
  for (target_edge_id in moderation_target_ids) {
    target_moderations <- Filter(
      function(item) identical(item$targetEdgeId, target_edge_id),
      spec$moderations
    )
    if (length(target_moderations) <= 1L) next

    target <- edge_for_id(target_edge_id)
    fit_name <- fit_key_by_outcome[[target$to]]
    fit <- fits[[fit_name]]
    coefficients <- coef(fit)
    covariance <- model_vcov(fit)
    is_glm_fit <- inherits(fit, "glm")
    critical <- if (is_glm_fit) {
      qnorm(1 - alpha / 2)
    } else {
      qt(1 - alpha / 2, df = df.residual(fit))
    }

    simple_w <- Filter(function(item) {
      if (!is.null(item$secondaryModeratorNodeId)) return(FALSE)
      moderator <- Filter(
        function(node) identical(node$id, item$moderatorNodeId),
        spec$nodes
      )[[1]]
      identical(moderator$role, "w")
    }, target_moderations)
    simple_z <- Filter(function(item) {
      if (!is.null(item$secondaryModeratorNodeId)) return(FALSE)
      moderator <- Filter(
        function(node) identical(node$id, item$moderatorNodeId),
        spec$nodes
      )[[1]]
      identical(moderator$role, "z")
    }, target_moderations)
    joint <- Filter(
      function(item) !is.null(item$secondaryModeratorNodeId),
      target_moderations
    )

    moderator_grid <- function(node, used) {
      if (!used || is.null(node)) {
        return(list(original = 0, model = 0, labels = "fixed"))
      }
      original_values_for_node <- original_values[[node$id]]
      values <- process_representative_values(original_values_for_node)
      labels <- names(values)
      center_value <- if (is.null(centering_means[[node$id]])) {
        0
      } else {
        centering_means[[node$id]]
      }
      list(original = values, model = values - center_value, labels = labels)
    }
    w_grid <- moderator_grid(w_node, length(simple_w) > 0L || length(joint) > 0L)
    z_grid <- moderator_grid(z_node, length(simple_z) > 0L || length(joint) > 0L)

    slope_terms <- target$from
    if (length(simple_w) > 0L) slope_terms <- c(slope_terms, simple_w[[1]]$productTermId)
    if (length(simple_z) > 0L) slope_terms <- c(slope_terms, simple_z[[1]]$productTermId)
    if (length(joint) > 0L) slope_terms <- c(slope_terms, joint[[1]]$productTermId)
    slope_covariance <- covariance[slope_terms, slope_terms, drop = FALSE]

    for (w_index in seq_along(w_grid$model)) {
      for (z_index in seq_along(z_grid$model)) {
        w_value <- w_grid$model[[w_index]]
        z_value <- z_grid$model[[z_index]]
        gradient <- 1
        if (length(simple_w) > 0L) gradient <- c(gradient, w_value)
        if (length(simple_z) > 0L) gradient <- c(gradient, z_value)
        if (length(joint) > 0L) gradient <- c(gradient, w_value * z_value)
        slope <- sum(unname(coefficients[slope_terms]) * gradient)
        variance <- as.numeric(t(gradient) %*% slope_covariance %*% gradient)
        standard_error <- sqrt(max(variance, 0))
        statistic <- if (standard_error > 0) slope / standard_error else NA_real_
        label_parts <- character(0)
        if (length(w_grid$model) > 1L) {
          label_parts <- c(label_parts, paste0("W_", w_grid$labels[[w_index]]))
        }
        if (length(z_grid$model) > 1L) {
          label_parts <- c(label_parts, paste0("Z_", z_grid$labels[[z_index]]))
        }
        probes[[length(probes) + 1L]] <- list(
          moderationId = paste(vapply(
            target_moderations, function(item) item$id, character(1)
          ), collapse = "__"),
          targetEdgeId = target$id,
          predictorLabel = node_label(target$from),
          moderatorLabel = if (length(w_grid$model) > 1L) node_label(w_node$id) else node_label(z_node$id),
          secondaryModeratorLabel = if (
            length(w_grid$model) > 1L && length(z_grid$model) > 1L
          ) node_label(z_node$id) else NULL,
          label = paste(label_parts, collapse = "__"),
          moderatorValue = if (length(w_grid$model) > 1L) {
            unname(w_grid$original[[w_index]])
          } else {
            unname(z_grid$original[[z_index]])
          },
          secondaryModeratorValue = if (
            length(w_grid$model) > 1L && length(z_grid$model) > 1L
          ) unname(z_grid$original[[z_index]]) else NULL,
          effect = slope,
          standardError = standard_error,
          statistic = statistic,
          pValue = if (!is.finite(statistic)) {
            NA_real_
          } else if (is_glm_fit) {
            2 * pnorm(abs(statistic), lower.tail = FALSE)
          } else {
            2 * pt(abs(statistic), df = df.residual(fit), lower.tail = FALSE)
          },
          confidenceInterval = list(
            level = spec$estimation$confidenceLevel,
            lower = slope - critical * standard_error,
            upper = slope + critical * standard_error,
            method = researchpath_confidence_interval_method(
              covariance, is_glm_fit, spec$estimation$standardErrors
            )
          )
        )
      }
    }
  }
}

if (template %in% c("model_2", "model_3")) {
  simple_mod_for_role <- function(role) {
    matches <- Filter(function(mod) {
      if (!is.null(mod$secondaryModeratorNodeId)) return(FALSE)
      moderator <- Filter(
        function(node) identical(node$id, mod$moderatorNodeId),
        spec$nodes
      )[[1]]
      identical(moderator$role, role)
    }, spec$moderations)
    matches[[1]]
  }
  w_mod <- simple_mod_for_role("w")
  z_mod <- simple_mod_for_role("z")
  joint_mods <- Filter(
    function(mod) !is.null(mod$secondaryModeratorNodeId),
    spec$moderations
  )
  joint_mod <- if (length(joint_mods) == 1) joint_mods[[1]] else NULL
  y_fit <- fits$y
  covariance <- model_vcov(y_fit)
  coefficients <- coef(y_fit)
  is_glm_fit <- inherits(y_fit, "glm")
  critical <- if (is_glm_fit) {
    qnorm(1 - alpha / 2)
  } else {
    qt(1 - alpha / 2, df = df.residual(y_fit))
  }

  moderator_grid <- function(node) {
    original <- original_values[[node$id]]
    values <- process_representative_values(original)
    center_value <- if (is.null(centering_means[[node$id]])) {
      0
    } else {
      centering_means[[node$id]]
    }
    list(original = values, model = values - center_value)
  }
  w_grid <- moderator_grid(w_node)
  z_grid <- moderator_grid(z_node)
  slope_terms <- c(x_node$id, w_mod$productTermId, z_mod$productTermId)
  if (!is.null(joint_mod)) slope_terms <- c(slope_terms, joint_mod$productTermId)
  slope_covariance <- covariance[slope_terms, slope_terms, drop = FALSE]

  for (w_index in seq_along(w_grid$model)) {
    for (z_index in seq_along(z_grid$model)) {
      w_value <- w_grid$model[[w_index]]
      z_value <- z_grid$model[[z_index]]
      gradient <- c(1, w_value, z_value)
      if (!is.null(joint_mod)) gradient <- c(gradient, w_value * z_value)
      slope <- sum(unname(coefficients[slope_terms]) * gradient)
      variance <- as.numeric(t(gradient) %*% slope_covariance %*% gradient)
      se <- sqrt(max(variance, 0))
      statistic <- slope / se
      probes[[length(probes) + 1]] <- list(
        moderationId = if (is.null(joint_mod)) {
          paste0(w_mod$id, "__", z_mod$id)
        } else {
          joint_mod$id
        },
        targetEdgeId = edge_for_id(w_mod$targetEdgeId)$id,
        predictorLabel = node_label(x_node$id),
        moderatorLabel = node_label(w_node$id),
        secondaryModeratorLabel = node_label(z_node$id),
        label = paste0(
          "W_", names(w_grid$original)[[w_index]],
          "__Z_", names(z_grid$original)[[z_index]]
        ),
        moderatorValue = unname(w_grid$original[[w_index]]),
        secondaryModeratorValue = unname(z_grid$original[[z_index]]),
        effect = slope,
        standardError = se,
        statistic = statistic,
        pValue = if (is_glm_fit) {
          2 * pnorm(abs(statistic), lower.tail = FALSE)
        } else {
          2 * pt(abs(statistic), df = df.residual(y_fit), lower.tail = FALSE)
        },
        confidenceInterval = list(
          level = spec$estimation$confidenceLevel,
          lower = slope - critical * se,
          upper = slope + critical * se,
          method = researchpath_confidence_interval_method(
            covariance, is_glm_fit, spec$estimation$standardErrors
          )
        )
      )
    }
  }
}
