# ResearchPath R Engine - RI-CLPM & Latent Growth Modeling (WP-LONG-01~03)

fit_riclpm_model <- function(data, x_waves, y_waves, estimator = "MLR", missing = "fiml") {
  suppressPackageStartupMessages(library(lavaan))

  if (length(x_waves) < 3 || length(y_waves) < 3) {
    stop("RI-CLPM 模型至少需要 3 个时间波段的数据")
  }

  num_waves <- min(length(x_waves), length(y_waves))

  # Build lavaan RI-CLPM syntax
  # 1. Random Intercepts
  ri_x_syntax <- paste0("RI_X =~ ", paste(paste0("1*", x_waves[1:num_waves]), collapse = " + "))
  ri_y_syntax <- paste0("RI_Y =~ ", paste(paste0("1*", y_waves[1:num_waves]), collapse = " + "))

  # 2. Within-person centered variables
  within_syntax <- c()
  for (t in 1:num_waves) {
    within_syntax <- c(within_syntax, paste0("wx_", t, " =~ 1*", x_waves[t]))
    within_syntax <- c(within_syntax, paste0("wy_", t, " =~ 1*", y_waves[t]))
    within_syntax <- c(within_syntax, paste0(x_waves[t], " ~~ 0*", x_waves[t]))
    within_syntax <- c(within_syntax, paste0(y_waves[t], " ~~ 0*", y_waves[t]))
    within_syntax <- c(within_syntax, paste0("wx_", t, " ~~ wy_", t))
  }

  # 3. Autoregressive and Cross-lagged paths
  clpm_paths <- c()
  for (t in 2:num_waves) {
    prev <- t - 1
    clpm_paths <- c(clpm_paths, paste0("wx_", t, " ~ a1*", "wx_", prev, " + c1*", "wy_", prev))
    clpm_paths <- c(clpm_paths, paste0("wy_", t, " ~ a2*", "wy_", prev, " + c2*", "wx_", prev))
  }

  model_syntax <- paste(c(ri_x_syntax, ri_y_syntax, within_syntax, clpm_paths), collapse = "\n")
  orthogonality <- c(
    paste0("RI_X ~~ 0*wx_", seq_len(num_waves)),
    paste0("RI_X ~~ 0*wy_", seq_len(num_waves)),
    paste0("RI_Y ~~ 0*wx_", seq_len(num_waves)),
    paste0("RI_Y ~~ 0*wy_", seq_len(num_waves)),
    "RI_X ~~ RI_Y"
  )
  model_syntax <- paste(c(model_syntax, orthogonality), collapse = "\n")

  fit <- lavaan::sem(model_syntax, data = data, estimator = estimator, missing = if (identical(missing, "fiml")) "fiml" else "listwise", auto.fix.first = FALSE, auto.var = TRUE)

  if (!lavInspect(fit, "converged")) {
    stop("RI-CLPM 模型拟合未收敛")
  }

  pe <- parameterEstimates(fit)
  cross_lagged <- pe[pe$op == "~" & pe$label %in% c("c1", "c2"), ]
  autoregressive <- pe[pe$op == "~" & pe$label %in% c("a1", "a2"), ]

  cross_lagged_results <- lapply(1:nrow(cross_lagged), function(i) {
    list(
      lhs = as.character(cross_lagged$lhs[i]),
      rhs = as.character(cross_lagged$rhs[i]),
      estimate = finite_number(cross_lagged$est[i]),
      standardError = finite_number(cross_lagged$se[i]),
      zValue = finite_number(cross_lagged$z[i]),
      pValue = finite_number(cross_lagged$pvalue[i])
    )
  })
  autoregressive_results <- lapply(1:nrow(autoregressive), function(i) {
    list(lhs = as.character(autoregressive$lhs[i]), rhs = as.character(autoregressive$rhs[i]),
      estimate = finite_number(autoregressive$est[i]), standardError = finite_number(autoregressive$se[i]),
      zValue = finite_number(autoregressive$z[i]), pValue = finite_number(autoregressive$pvalue[i]))
  })
  trait_row <- function(lhs, rhs = lhs) {
    row <- pe[pe$op == "~~" & pe$lhs == lhs & pe$rhs == rhs, , drop = FALSE]
    if (nrow(row) == 0L && lhs != rhs) row <- pe[pe$op == "~~" & pe$lhs == rhs & pe$rhs == lhs, , drop = FALSE]
    finite_number(row$est[[1]])
  }

  fit_m <- fitMeasures(fit, c("chisq", "df", "pvalue", "cfi", "tli", "rmsea", "srmr"))

  missing_patterns <- NULL
  if (identical(missing, "fiml")) {
    pats <- tryCatch(lavaan::lavInspect(fit, "patterns"), error = function(e) NULL)
    if (!is.null(pats)) {
      missing_patterns <- as.integer(nrow(pats))
    }
  }

  list(
    available = TRUE,
    modelType = "RI-CLPM",
    sampleSize = as.integer(lavaan::lavInspect(fit, "ntotal")),
    missingMethod = missing,
    missingPatterns = missing_patterns,
    numWaves = num_waves,
    converged = TRUE,
    fitIndices = list(
      chiSquare = finite_number(fit_m["chisq"]),
      df = as.integer(fit_m["df"]),
      pValue = finite_number(fit_m["pvalue"]),
      cfi = finite_number(fit_m["cfi"]),
      tli = finite_number(fit_m["tli"]),
      rmsea = finite_number(fit_m["rmsea"]),
      srmr = finite_number(fit_m["srmr"])
    ),
    traitComponents = list(var_RI_X = trait_row("RI_X"), var_RI_Y = trait_row("RI_Y"),
      cov_RI = trait_row("RI_X", "RI_Y")),
    autoregressiveEffects = autoregressive_results,
    crossLaggedEffects = cross_lagged_results
  )
}
