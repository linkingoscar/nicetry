lcm_sr_state_names <- function(wave_count) {
  list(
    x = paste0("wx_", seq_len(wave_count)),
    y = paste0("wy_", seq_len(wave_count))
  )
}

lcm_sr_growth_names <- function(growth_shape) {
  base <- list(x = c("GX_I", "GX_S"), y = c("GY_I", "GY_S"))
  if (identical(growth_shape, "quadratic")) {
    base$x <- c(base$x, "GX_Q")
    base$y <- c(base$y, "GY_Q")
  }
  base
}

lcm_sr_structural_syntax <- function(factors, waves, constrained, growth_shape) {
  wave_count <- length(factors$x)
  time_values <- vapply(waves, function(wave) as.numeric(wave$timeValue), numeric(1))
  origin <- time_values[[1]]
  centered_time <- time_values - origin
  state <- lcm_sr_state_names(wave_count)
  growth <- lcm_sr_growth_names(growth_shape)
  label <- function(prefix, index) if (constrained) prefix else paste0(prefix, index)
  loading_line <- function(name, factor_names, loadings) {
    paste0(
      name,
      " =~ ",
      paste(paste0(format(loadings, scientific = FALSE, trim = TRUE), "*", factor_names), collapse = " + ")
    )
  }
  syntax <- c(
    loading_line("GX_I", factors$x, rep(1, wave_count)),
    loading_line("GX_S", factors$x, centered_time),
    loading_line("GY_I", factors$y, rep(1, wave_count)),
    loading_line("GY_S", factors$y, centered_time)
  )
  if (identical(growth_shape, "quadratic")) {
    syntax <- c(
      syntax,
      loading_line("GX_Q", factors$x, centered_time^2),
      loading_line("GY_Q", factors$y, centered_time^2)
    )
  }
  syntax <- c(
    syntax,
    paste0(unlist(growth, use.names = FALSE), " ~ 1")
  )
  for (index in seq_len(wave_count)) {
    syntax <- c(
      syntax,
      paste0(state$x[[index]], " =~ 1*", factors$x[[index]]),
      paste0(state$y[[index]], " =~ 1*", factors$y[[index]]),
      paste0(factors$x[[index]], " ~~ 0*", factors$x[[index]]),
      paste0(factors$y[[index]], " ~~ 0*", factors$y[[index]]),
      paste0(factors$x[[index]], " ~ 0*1"),
      paste0(factors$y[[index]], " ~ 0*1"),
      paste0(state$x[[index]], " ~~ ", state$y[[index]])
    )
    for (growth_name in unlist(growth, use.names = FALSE)) {
      syntax <- c(
        syntax,
        paste0(growth_name, " ~~ 0*", state$x[[index]]),
        paste0(growth_name, " ~~ 0*", state$y[[index]])
      )
    }
    if (index > 1L) {
      previous <- index - 1L
      syntax <- c(
        syntax,
        sprintf(
          "%s ~ %s*%s + %s*%s",
          state$x[[index]], label("ar_x", previous), state$x[[previous]],
          label("cl_yx", previous), state$y[[previous]]
        ),
        sprintf(
          "%s ~ %s*%s + %s*%s",
          state$y[[index]], label("ar_y", previous), state$y[[previous]],
          label("cl_xy", previous), state$x[[previous]]
        )
      )
    }
  }
  list(
    syntax = syntax,
    origin = origin,
    centeredTime = centered_time,
    state = state,
    growth = growth
  )
}

lcm_sr_growth_rows <- function(fit, growth_shape, confidence_level) {
  growth_names <- unlist(lcm_sr_growth_names(growth_shape), use.names = FALSE)
  parameters <- lavaan::parameterEstimates(
    fit,
    standardized = TRUE,
    ci = TRUE,
    level = confidence_level
  )
  selected <- parameters[
    (parameters$op == "~1" & parameters$lhs %in% growth_names) |
      (
        parameters$op == "~~" &
          parameters$lhs %in% growth_names &
          parameters$rhs %in% growth_names
      ),
    ,
    drop = FALSE
  ]
  lapply(seq_len(nrow(selected)), function(index) {
    list(
      lhs = as.character(selected$lhs[[index]]),
      operator = as.character(selected$op[[index]]),
      rhs = if (identical(selected$op[[index]], "~1")) {
        NULL
      } else {
        as.character(selected$rhs[[index]])
      },
      estimate = panel_finite(selected$est[[index]]),
      standardizedEstimate = panel_finite(selected$std.all[[index]]),
      standardError = panel_finite(selected$se[[index]]),
      pValue = panel_finite(selected$pvalue[[index]]),
      lower = panel_finite(selected$ci.lower[[index]]),
      upper = panel_finite(selected$ci.upper[[index]])
    )
  })
}

lcm_sr_result <- function(fit, spec, confidence_level) {
  time_values <- vapply(spec$waves, function(wave) as.numeric(wave$timeValue), numeric(1))
  covariance <- tryCatch(lavaan::lavInspect(fit, "cov.lv"), error = function(error) NULL)
  minimum_eigenvalue <- if (is.null(covariance)) {
    NA_real_
  } else {
    min(eigen((covariance + t(covariance)) / 2, symmetric = TRUE, only.values = TRUE)$values)
  }
  growth_names <- unlist(lcm_sr_growth_names(spec$growthShape), use.names = FALSE)
  parameters <- lavaan::parameterEstimates(fit)
  negative_growth_variances <- parameters[
    parameters$op == "~~" &
      parameters$lhs == parameters$rhs &
      parameters$lhs %in% growth_names &
      parameters$est < -1e-8,
    ,
    drop = FALSE
  ]
  list(
    growthShape = spec$growthShape,
    timeOrigin = time_values[[1]],
    timeLoadings = as.list(time_values - time_values[[1]]),
    components = lcm_sr_growth_rows(fit, spec$growthShape, confidence_level),
    identification = list(
      converged = isTRUE(lavaan::lavInspect(fit, "converged")),
      postCheckPassed = isTRUE(lavaan::lavInspect(fit, "post.check")),
      latentCovarianceMinimumEigenvalue = panel_finite(minimum_eigenvalue),
      negativeGrowthVarianceCount = nrow(negative_growth_variances),
      valid = isTRUE(lavaan::lavInspect(fit, "converged")) &&
        isTRUE(lavaan::lavInspect(fit, "post.check")) &&
        is.finite(minimum_eigenvalue) &&
        minimum_eigenvalue > -1e-8 &&
        nrow(negative_growth_variances) == 0L
    ),
    interpretation = paste0(
      "生长因子刻画跨被试的宏观轨迹，结构化残差的自回归与交叉滞后路径刻画",
      "相对个体轨迹的时点内偏离。"
    )
  )
}
