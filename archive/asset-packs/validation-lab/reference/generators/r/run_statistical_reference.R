args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_statistical_reference.R <case-dir> <output.json>")
suppressPackageStartupMessages(library(jsonlite))

case_dir <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
manifest <- yaml::read_yaml(file.path(case_dir, "manifest.yaml"))
spec <- jsonlite::fromJSON(file.path(case_dir, manifest$specPath), simplifyVector = FALSE)
data <- utils::read.csv(file.path(case_dir, "data", "input.csv"), check.names = FALSE,
  stringsAsFactors = FALSE)
capability <- manifest$identity$capabilityId

result <- switch(capability,
  "measurement.efa.continuous.minres.v1" = {
    variables <- unlist(spec$variables)
    frame <- data[, variables, drop = FALSE]
    correlation <- stats::cor(frame, use = "pairwise.complete.obs")
    fit <- psych::fa(r = correlation, nfactors = as.integer(spec$nFactors),
      n.obs = nrow(frame), fm = "minres", rotate = "promax")
    loadings <- unclass(fit$loadings)
    phi <- if (is.null(fit$Phi)) diag(ncol(loadings)) else unclass(fit$Phi)
    list(n_factors = as.integer(spec$nFactors),
      loadings = lapply(seq_len(nrow(loadings)), function(index) as.list(unname(loadings[index, ]))),
      communalities = as.list(unname(diag(loadings %*% phi %*% t(loadings)))))
  },
  "equivalence.tost.two_sample.v1" = {
    group <- factor(data[[spec$data$groupVar]])
    values <- as.numeric(data[[spec$data$outcomeVar]])
    levels <- levels(group); first <- values[group == levels[[1]]]; second <- values[group == levels[[2]]]
    difference <- mean(first) - mean(second)
    degrees <- length(first) + length(second) - 2L
    pooled_sd <- sqrt(((length(first) - 1) * stats::var(first) +
      (length(second) - 1) * stats::var(second)) / degrees)
    standard_error <- pooled_sd * sqrt(1 / length(first) + 1 / length(second))
    lower_t <- (difference - spec$parameters$lowBound) / standard_error
    upper_t <- (difference - spec$parameters$highBound) / standard_error
    lower_p <- stats::pt(lower_t, degrees, lower.tail = FALSE)
    upper_p <- stats::pt(upper_t, degrees)
    equivalent <- max(lower_p, upper_p) < spec$parameters$alpha
    list(tost_results = list(mean_diff = difference, se = standard_error,
      t_lower = lower_t, p_lower = lower_p, t_upper = upper_t, p_upper = upper_p,
      equivalent = equivalent, decision = if (equivalent) "equivalent" else "not_equivalent"),
      diagnostics = list(converged = TRUE))
  },
  "experiment.posthoc.games_howell.v1" = {
    group <- factor(data[[spec$data$groupVar]])
    values <- as.numeric(data[[spec$data$outcomeVar]])
    levels <- levels(group); summaries <- lapply(levels, function(level) {
      current <- values[group == level]
      list(level = level, n = length(current), mean = mean(current), variance = stats::var(current))
    })
    pairs <- utils::combn(seq_along(summaries), 2L)
    contrasts <- lapply(seq_len(ncol(pairs)), function(index) {
      left <- summaries[[pairs[1, index]]]; right <- summaries[[pairs[2, index]]]
      left_component <- left$variance / left$n; right_component <- right$variance / right$n
      standard_error <- sqrt(left_component + right_component)
      degrees <- (left_component + right_component)^2 /
        (left_component^2 / (left$n - 1L) + right_component^2 / (right$n - 1L))
      difference <- right$mean - left$mean
      q_value <- sqrt(2) * abs(difference) / standard_error
      list(comparison = paste0(right$level, " - ", left$level), estimate = difference,
        se = standard_error, df = degrees, statistic = difference / standard_error,
        p_value = stats::ptukey(q_value, nmeans = length(levels), df = degrees,
          lower.tail = FALSE))
    })
    list(contrasts = contrasts, diagnostics = list(converged = TRUE))
  },
  "experiment.randomization.inference.v1" = {
    treatment <- as.numeric(data[[spec$data$treatmentVar]])
    outcome <- as.numeric(data[[spec$data$outcomeVar]])
    treated_count <- sum(treatment == 1)
    observed <- mean(outcome[treatment == 1]) - mean(outcome[treatment == 0])
    assignments <- utils::combn(seq_along(outcome), treated_count)
    statistics <- apply(assignments, 2L, function(indices) mean(outcome[indices]) - mean(outcome[-indices]))
    list(observed_stat = observed, permutations_total = ncol(assignments),
      p_value_two_sided = mean(abs(statistics) >= abs(observed) - 1e-12),
      diagnostics = list(converged = TRUE))
  },
  "multilevel.lmm.within_between.v1" = {
    cluster <- spec$data$clusterVar; predictor <- spec$data$predictor; outcome <- spec$data$outcome
    between <- ave(data[[predictor]], data[[cluster]], FUN = mean)
    transformed <- data.frame(y = data[[outcome]], x_within = data[[predictor]] - between,
      x_between = between)
    table <- summary(stats::lm(y ~ x_within + x_between, data = transformed))$coefficients
    list(fixed_effects = lapply(seq_len(nrow(table)), function(index) list(
      term = rownames(table)[[index]], estimate = unname(table[index, "Estimate"]),
      se = unname(table[index, "Std. Error"]), statistic = unname(table[index, "t value"]),
      p_value = unname(table[index, "Pr(>|t|)"]))), diagnostics = list(converged = TRUE))
  },
  stop(paste0("REFERENCE_CAPABILITY_NOT_IMPLEMENTED: ", capability), call. = FALSE)
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE,
  null = "null", na = "null", digits = NA)
