fit_polynomial_response_surface <- function(data, outcome_id, predictor_ids, control_ids, label_lookup, confidence_level = 0.95) {
  confidence_level <- researchpath_validate_confidence_level(confidence_level)
  if (length(predictor_ids) != 2L) {
    return(list(available = FALSE, confidenceLevel = confidence_level, reason = "响应面分析需要恰好两个焦点预测变量"))
  }
  x_id <- predictor_ids[[1]]
  z_id <- predictor_ids[[2]]
  required <- unique(c(outcome_id, x_id, z_id, control_ids))
  frame <- data[, required, drop = FALSE]
  frame <- frame[complete.cases(frame), , drop = FALSE]
  if (nrow(frame) < length(required) + 10L) {
    return(list(available = FALSE, confidenceLevel = confidence_level, reason = "响应面完整案例不足"))
  }
  if (sd(frame[[x_id]]) <= 0 || sd(frame[[z_id]]) <= 0) {
    return(list(available = FALSE, confidenceLevel = confidence_level, reason = "焦点预测变量缺少变异"))
  }

  x_mean <- mean(frame[[x_id]])
  z_mean <- mean(frame[[z_id]])
  frame$.rp_y <- frame[[outcome_id]]
  frame$.rp_x <- frame[[x_id]] - x_mean
  frame$.rp_z <- frame[[z_id]] - z_mean
  frame$.rp_x2 <- frame$.rp_x^2
  frame$.rp_xz <- frame$.rp_x * frame$.rp_z
  frame$.rp_z2 <- frame$.rp_z^2
  model_formula <- reformulate(
    c(".rp_x", ".rp_z", ".rp_x2", ".rp_xz", ".rp_z2", control_ids),
    response = ".rp_y"
  )
  fit <- tryCatch(lm(model_formula, data = frame), error = function(error) NULL)
  if (is.null(fit) || any(!is.finite(coef(fit)))) {
    return(list(available = FALSE, confidenceLevel = confidence_level, reason = "多项式回归不可估计或设计矩阵奇异"))
  }

  coefficient_names <- names(coef(fit))
  covariance <- vcov(fit)
  degrees <- df.residual(fit)
  critical <- qt(1 - (1 - confidence_level) / 2, degrees)
  coefficient_label <- c(
    "(Intercept)" = "常数", ".rp_x" = paste0(label_lookup(x_id), " (X)"),
    ".rp_z" = paste0(label_lookup(z_id), " (Z)"), ".rp_x2" = "X²",
    ".rp_xz" = "X×Z", ".rp_z2" = "Z²"
  )
  coefficients <- lapply(seq_along(coefficient_names), function(index) {
    term <- coefficient_names[[index]]
    estimate <- coef(fit)[[index]]
    standard_error <- sqrt(covariance[index, index])
    statistic <- estimate / standard_error
    list(
      term = term,
      label = if (term %in% names(coefficient_label)) coefficient_label[[term]] else label_lookup(term),
      estimate = finite_number(estimate),
      standardError = finite_number(standard_error),
      statistic = finite_number(statistic),
      pValue = finite_number(2 * pt(abs(statistic), df = degrees, lower.tail = FALSE)),
      lower = finite_number(estimate - critical * standard_error),
      upper = finite_number(estimate + critical * standard_error)
    )
  })

  surface_test <- function(id, label, weights) {
    contrast <- setNames(rep(0, length(coefficient_names)), coefficient_names)
    contrast[names(weights)] <- weights
    estimate <- sum(contrast * coef(fit))
    standard_error <- sqrt(as.numeric(t(contrast) %*% covariance %*% contrast))
    statistic <- estimate / standard_error
    list(
      id = id, label = label, estimate = finite_number(estimate),
      standardError = finite_number(standard_error), statistic = finite_number(statistic),
      pValue = finite_number(2 * pt(abs(statistic), df = degrees, lower.tail = FALSE)),
      lower = finite_number(estimate - critical * standard_error),
      upper = finite_number(estimate + critical * standard_error)
    )
  }
  surface_tests <- list(
    surface_test("a1", "一致线斜率 a1 = b1 + b2", c(".rp_x" = 1, ".rp_z" = 1)),
    surface_test("a2", "一致线曲率 a2 = b3 + b4 + b5", c(".rp_x2" = 1, ".rp_xz" = 1, ".rp_z2" = 1)),
    surface_test("a3", "不一致线斜率 a3 = b1 - b2", c(".rp_x" = 1, ".rp_z" = -1)),
    surface_test("a4", "不一致线曲率 a4 = b3 - b4 + b5", c(".rp_x2" = 1, ".rp_xz" = -1, ".rp_z2" = 1))
  )

  b <- coef(fit)
  hessian <- matrix(c(2 * b[[".rp_x2"]], b[[".rp_xz"]], b[[".rp_xz"]], 2 * b[[".rp_z2"]]), 2, 2)
  stationary <- tryCatch(
    as.numeric(solve(hessian, -c(b[[".rp_x"]], b[[".rp_z"]]))),
    error = function(error) c(NA_real_, NA_real_)
  )
  eigenvalues <- tryCatch(eigen(hessian, symmetric = TRUE)$values, error = function(error) c(NA_real_, NA_real_))

  x_values <- seq(quantile(frame[[x_id]], 0.05), quantile(frame[[x_id]], 0.95), length.out = 9)
  z_values <- seq(quantile(frame[[z_id]], 0.05), quantile(frame[[z_id]], 0.95), length.out = 9)
  grid <- expand.grid(.rp_x_raw = x_values, .rp_z_raw = z_values)
  grid$.rp_x <- grid$.rp_x_raw - x_mean
  grid$.rp_z <- grid$.rp_z_raw - z_mean
  grid$.rp_x2 <- grid$.rp_x^2
  grid$.rp_xz <- grid$.rp_x * grid$.rp_z
  grid$.rp_z2 <- grid$.rp_z^2
  for (control_id in control_ids) {
    values <- frame[[control_id]]
    grid[[control_id]] <- if (is.numeric(values)) mean(values) else names(sort(table(values), decreasing = TRUE))[[1]]
  }
  grid$predicted <- as.numeric(predict(fit, newdata = grid))
  grid_rows <- lapply(seq_len(nrow(grid)), function(index) list(
    x = finite_number(grid$.rp_x_raw[[index]]),
    z = finite_number(grid$.rp_z_raw[[index]]),
    predicted = finite_number(grid$predicted[[index]])
  ))

  list(
    available = TRUE, confidenceLevel = confidence_level, outcomeId = outcome_id, outcomeLabel = label_lookup(outcome_id),
    xId = x_id, xLabel = label_lookup(x_id), zId = z_id, zLabel = label_lookup(z_id),
    n = nrow(frame), centering = list(xMean = finite_number(x_mean), zMean = finite_number(z_mean)),
    formula = paste(deparse(formula(fit)), collapse = " "),
    rSquared = finite_number(summary(fit)$r.squared),
    adjustedRSquared = finite_number(summary(fit)$adj.r.squared),
    coefficients = coefficients, surfaceTests = surface_tests,
    stationaryPoint = list(
      xCentered = finite_number(stationary[[1]]), zCentered = finite_number(stationary[[2]]),
      xRaw = finite_number(stationary[[1]] + x_mean), zRaw = finite_number(stationary[[2]] + z_mean),
      hessianEigenvalues = as.list(vapply(eigenvalues, finite_number, numeric(1)))
    ),
    grid = grid_rows,
    method = "centered second-order polynomial OLS; controls held at means/modes for the response grid"
  )
}
