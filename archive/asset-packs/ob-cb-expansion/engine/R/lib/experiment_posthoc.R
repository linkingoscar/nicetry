# Explicit, dependency-light post-hoc estimators for the supported experimental slices.

fit_games_howell <- function(data, outcome, group, confidence_level = 0.95) {
  frame <- data[, c(outcome, group), drop = FALSE]
  names(frame) <- c("outcome", "group")
  frame <- frame[complete.cases(frame), , drop = FALSE]
  frame$group <- droplevels(factor(frame$group))
  group_names <- levels(frame$group)
  if (length(group_names) < 2L) stop("GAMES_HOWELL_REQUIRES_TWO_GROUPS", call. = FALSE)

  summaries <- lapply(group_names, function(level) {
    values <- frame$outcome[frame$group == level]
    if (length(values) < 2L) stop("GAMES_HOWELL_GROUP_REQUIRES_TWO_OBSERVATIONS", call. = FALSE)
    variance <- stats::var(values)
    if (!is.finite(variance)) stop("GAMES_HOWELL_GROUP_VARIANCE_UNAVAILABLE", call. = FALSE)
    list(level = level, n = length(values), mean = mean(values), variance = variance)
  })

  alpha <- 1 - as.numeric(confidence_level)
  result <- list()
  for (left_index in seq_len(length(summaries) - 1L)) {
    for (right_index in seq.int(left_index + 1L, length(summaries))) {
      left <- summaries[[left_index]]
      right <- summaries[[right_index]]
      left_component <- left$variance / left$n
      right_component <- right$variance / right$n
      standard_error <- sqrt(left_component + right_component)
      if (!is.finite(standard_error) || standard_error <= 0) {
        stop("GAMES_HOWELL_STANDARD_ERROR_UNAVAILABLE", call. = FALSE)
      }
      degrees <- (left_component + right_component)^2 / (
        left_component^2 / (left$n - 1L) + right_component^2 / (right$n - 1L)
      )
      if (!is.finite(degrees) || degrees <= 0) {
        stop("GAMES_HOWELL_DEGREES_OF_FREEDOM_UNAVAILABLE", call. = FALSE)
      }
      difference <- right$mean - left$mean
      q_statistic <- sqrt(2) * abs(difference) / standard_error
      critical_q <- stats::qtukey(1 - alpha, nmeans = length(summaries), df = degrees) / sqrt(2)
      p_value <- stats::ptukey(q_statistic, nmeans = length(summaries), df = degrees, lower.tail = FALSE)
      result[[length(result) + 1L]] <- list(
        contrast = paste0(right$level, " - ", left$level),
        group1 = left$level,
        group2 = right$level,
        estimate = finite_number(difference),
        standardError = finite_number(standard_error),
        degreesOfFreedom = finite_number(degrees),
        qStatistic = finite_number(q_statistic),
        pValue = finite_number(p_value),
        confidenceLower = finite_number(difference - critical_q * standard_error),
        confidenceUpper = finite_number(difference + critical_q * standard_error),
        adjustment = "games_howell",
        method = "Games-Howell studentized-range test"
      )
    }
  }
  result
}
