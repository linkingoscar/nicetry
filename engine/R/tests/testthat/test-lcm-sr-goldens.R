# Golden test: latent LCM-SR path vs a direct lavaan fit of the independently
# reconstructed configural-measurement + LCM-SR-structural syntax on a
# deterministic synthetic latent panel.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "lcm-sr-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
panel_path <- file.path(data_dir, "longitudinal", "panel_lcm_sr.csv")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

lcm_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
lcm_tolerance <- lcm_oracle$provenance$tolerance

source_engine("lib/runtime.R")
source_engine("lib/diary_utils.R")
source_engine("lib/longitudinal_lcm_sr.R")
source_engine("lib/longitudinal_latent.R")
source_engine("lib/longitudinal_panel.R")

test_that("latent LCM-SR matches the direct lavaan fit", {
  skip_if(is.null(lcm_oracle) || !file.exists(panel_path),
    "LCM-SR golden assets absent")
  data <- read.csv(panel_path, check.names = FALSE)
  spec <- list(
    measurementMode = "latent_items",
    subjectVariableId = "subject",
    waves = list(
      list(label = "W1", timeValue = 0,
           xItemIds = c("x1i1", "x1i2", "x1i3"), yItemIds = c("y1i1", "y1i2", "y1i3")),
      list(label = "W2", timeValue = 1,
           xItemIds = c("x2i1", "x2i2", "x2i3"), yItemIds = c("y2i1", "y2i2", "y2i3")),
      list(label = "W3", timeValue = 2,
           xItemIds = c("x3i1", "x3i2", "x3i3"), yItemIds = c("y3i1", "y3i2", "y3i3"))
    ),
    modelType = "lcm_sr",
    growthShape = "linear",
    indicatorScale = "continuous",
    invarianceLevel = "configural",
    partialInvariancePositions = list(),
    estimator = "MLR",
    missing = "listwise",
    constrainAcrossTime = FALSE,
    compareCompetingModels = FALSE,
    runRobustnessChecks = FALSE
  )
  result <- fit_longitudinal_panel(data, spec, function(id) id, 0.95)

  expect_true(isTRUE(result$available), info = "LCM-SR must be available")
  expect_identical(result$modelType, "lcm_sr")
  expect_equal(result$sampleSize, 300L, info = "LCM-SR sample size")

  fit_fields <- c("chiSquare", "degreesOfFreedom", "pValue", "cfi", "tli", "rmsea", "srmr")
  for (field in fit_fields) {
    expect_equal(
      as.numeric(result$fitIndices[[field]]), lcm_oracle$fit[[field]],
      tolerance = lcm_tolerance$fit,
      info = paste0("LCM-SR fit ", field)
    )
  }

  engine_components <- result$growthModel$components
  expect_equal(length(engine_components), length(lcm_oracle$growthComponents),
    info = "growth component count")
  for (index in seq_along(lcm_oracle$growthComponents)) {
    grow <- lcm_oracle$growthComponents[[index]]
    erow <- engine_components[[index]]
    expect_identical(erow$lhs, grow$lhs, info = paste0("growth row ", index, " lhs"))
    expect_identical(erow$operator, grow$operator, info = paste0("growth row ", index, " op"))
    expect_equal(as.numeric(erow$estimate), as.numeric(grow$estimate),
      tolerance = lcm_tolerance$growth, info = paste0("growth row ", index, " est"))
    engine_se <- suppressWarnings(as.numeric(erow$standardError))
    golden_se <- if (is.null(grow$standardError)) NA_real_ else suppressWarnings(as.numeric(grow$standardError))
    if (is.finite(engine_se) && is.finite(golden_se)) {
      expect_equal(engine_se, golden_se,
        tolerance = 1e-5, info = paste0("growth row ", index, " se"))
    }
  }
})
