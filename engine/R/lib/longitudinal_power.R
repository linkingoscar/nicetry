# 独立加载（测试/复用）时引导 seed 工具；入口脚本已先行 source。
if (!exists("researchpath_seed", mode = "function", inherits = TRUE)) {
  if (file.exists(file.path("engine", "R", "lib", "seed_utils.R"))) {
    source(file.path("engine", "R", "lib", "seed_utils.R"))
  }
}

power_finite <- function(value) {
  numeric_value <- suppressWarnings(as.numeric(value))
  if (length(numeric_value) == 0L || !is.finite(numeric_value[[1]])) {
    return(NULL)
  }
  numeric_value[[1]]
}

power_problem_rows <- function(problems) {
  if (is.null(problems) || length(problems) == 0L) return(list())
  if (is.data.frame(problems)) {
    return(lapply(seq_len(nrow(problems)), function(index) {
      row <- as.list(problems[index, , drop = FALSE])
      lapply(row, function(value) {
        if (length(value) == 1L && is.atomic(value) && is.na(value)) NULL else value
      })
    }))
  }
  list(list(message = paste(capture.output(print(problems)), collapse = "\n")))
}

longitudinal_power_analysis <- function(spec) {
  power_spec <- spec$powerAnalysis
  if (is.null(power_spec)) return(NULL)
  if (!identical(spec$modelType, "ri_clpm") || length(spec$waves) < 3L) {
    stop("LONGITUDINAL_POWER_REQUIRES_RI_CLPM_WITH_THREE_WAVES")
  }
  if (!requireNamespace("powRICLPM", quietly = TRUE)) {
    stop("POWRICLPM_PACKAGE_NOT_AVAILABLE")
  }

  sample_sizes <- as.integer(unlist(power_spec$sampleSizes))
  phi <- matrix(
    c(
      power_spec$autoregressiveX,
      power_spec$crossLaggedYToX,
      power_spec$crossLaggedXToY,
      power_spec$autoregressiveY
    ),
    nrow = 2L,
    byrow = TRUE
  )
  captured_warnings <- character(0)
  simulation <- withCallingHandlers(
    powRICLPM::powRICLPM(
      sample_size = sample_sizes,
      time_points = length(spec$waves),
      ICC = power_spec$icc,
      RI_cor = power_spec$randomInterceptCorrelation,
      Phi = phi,
      within_cor = power_spec$withinCorrelation,
      reliability = power_spec$reliability,
      estimate_ME = isTRUE(power_spec$estimateMeasurementError),
      significance_criterion = power_spec$alpha,
      reps = as.integer(power_spec$replications),
      seed = researchpath_seed(power_spec$seed),
      constraints = if (isTRUE(spec$constrainAcrossTime)) "lagged" else "none",
      estimator = if (identical(spec$estimator, "ML")) "ML" else "MLR",
      software = "lavaan"
    ),
    warning = function(warning) {
      captured_warnings <<- c(captured_warnings, conditionMessage(warning))
      invokeRestart("muffleWarning")
    }
  )

  parameters <- list(
    list(id = "x_to_y", label = "X→Y", parameter = "wB2~wA1"),
    list(id = "y_to_x", label = "Y→X", parameter = "wA2~wB1")
  )
  rows <- unlist(lapply(parameters, function(parameter) {
    raw <- powRICLPM::give(
      simulation,
      what = "results",
      parameter = parameter$parameter
    )
    lapply(seq_len(nrow(raw)), function(index) {
      list(
        direction = parameter$id,
        directionLabel = parameter$label,
        sampleSize = as.integer(raw$sample_size[[index]]),
        timePoints = as.integer(raw$time_points[[index]]),
        populationValue = power_finite(raw$population_value[[index]]),
        averageEstimate = power_finite(raw$average[[index]]),
        bias = power_finite(raw$bias[[index]]),
        empiricalStandardError = power_finite(raw$EmpSE[[index]]),
        averageStandardError = power_finite(raw$SEAvg[[index]]),
        mse = power_finite(raw$MSE[[index]]),
        coverage = power_finite(raw$coverage[[index]]),
        coverageMcse = {
          coverage <- power_finite(raw$coverage[[index]])
          if (is.null(coverage)) NULL else {
            sqrt(coverage * (1 - coverage) / as.integer(power_spec$replications))
          }
        },
        power = power_finite(raw$power[[index]]),
        powerMcse = {
          power <- power_finite(raw$power[[index]])
          if (is.null(power)) NULL else {
            sqrt(power * (1 - power) / as.integer(power_spec$replications))
          }
        }
      )
    })
  }), recursive = FALSE)

  recommendation_rows <- lapply(sample_sizes, function(sample_size) {
    matching <- Filter(function(row) identical(row$sampleSize, sample_size), rows)
    powers <- vapply(matching, function(row) {
      if (is.null(row$power)) NA_real_ else row$power
    }, numeric(1))
    list(
      sampleSize = sample_size,
      minimumDirectionalPower = if (all(is.na(powers))) NULL else min(powers, na.rm = TRUE),
      meetsTarget = length(powers) == length(parameters) &&
        all(is.finite(powers)) &&
        all(powers >= power_spec$targetPower)
    )
  })
  adequate <- Filter(function(row) isTRUE(row$meetsTarget), recommendation_rows)

  problems <- tryCatch(
    powRICLPM::give(simulation, what = "estimation_problems"),
    error = function(error) list(message = conditionMessage(error))
  )
  list(
    method = "Monte Carlo RI-CLPM power analysis",
    targetPower = power_spec$targetPower,
    alpha = power_spec$alpha,
    replications = as.integer(power_spec$replications),
    seed = researchpath_seed(power_spec$seed),
    assumptions = list(
      autoregressiveX = power_spec$autoregressiveX,
      autoregressiveY = power_spec$autoregressiveY,
      crossLaggedXToY = power_spec$crossLaggedXToY,
      crossLaggedYToX = power_spec$crossLaggedYToX,
      icc = power_spec$icc,
      randomInterceptCorrelation = power_spec$randomInterceptCorrelation,
      withinCorrelation = power_spec$withinCorrelation,
      reliability = power_spec$reliability,
      estimateMeasurementError = isTRUE(power_spec$estimateMeasurementError)
    ),
    results = rows,
    recommendationGrid = recommendation_rows,
    recommendedSampleSize = if (length(adequate) == 0L) NULL else adequate[[1]]$sampleSize,
    estimationProblems = power_problem_rows(problems),
    warnings = as.list(unique(captured_warnings)),
    validForPlanning = length(rows) > 0L &&
      all(vapply(rows, function(row) !is.null(row$power), logical(1))),
    provenance = list(
      engine = "R powRICLPM",
      engineVersion = as.character(utils::packageVersion("powRICLPM")),
      targetParameters = c("wB2~wA1", "wA2~wB1")
    )
  )
}
