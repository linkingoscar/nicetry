# Golden test: longitudinal panel path (CLPM / RI-CLPM) vs direct lavaan fits
# of the independently reconstructed model syntax on a deterministic
# synthetic panel.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "longitudinal-goldens-v1.json")
data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
panel_path <- file.path(data_dir, "longitudinal", "panel_clpm.csv")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

longitudinal_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
longitudinal_tolerance <- longitudinal_oracle$provenance$tolerance

source_engine("lib/runtime.R")
source_engine("lib/diary_utils.R")
source_engine("lib/longitudinal_panel.R")

panel_spec <- function(model_type) {
  list(
    waves = list(
      list(label = "W1", timeValue = 1, xVariableId = "x1", yVariableId = "y1"),
      list(label = "W2", timeValue = 2, xVariableId = "x2", yVariableId = "y2"),
      list(label = "W3", timeValue = 3, xVariableId = "x3", yVariableId = "y3"),
      list(label = "W4", timeValue = 4, xVariableId = "x4", yVariableId = "y4")
    ),
    modelType = model_type,
    subjectVariableId = "subject",
    constrainAcrossTime = FALSE,
    estimator = "ML",
    missing = "listwise",
    compareCompetingModels = FALSE,
    runRobustnessChecks = FALSE
  )
}

check_panel <- function(result, golden, label) {
  expect_true(isTRUE(result$available), info = paste0(label, ": available"))
  expect_equal(result$sampleSize, 400L, info = paste0(label, ": sample size"))
  expect_equal(result$waveCount, 4L, info = paste0(label, ": wave count"))

  fit_fields <- c("chiSquare", "degreesOfFreedom", "pValue", "cfi", "tli", "rmsea", "srmr")
  for (field in fit_fields) {
    expect_equal(
      as.numeric(result$fitIndices[[field]]), golden$fit[[field]],
      tolerance = longitudinal_tolerance$fit,
      info = paste0(label, ": fit ", field)
    )
  }

  engine_paths <- stats::setNames(result$paths,
    vapply(result$paths, `[[`, character(1), "id"))
  expect_equal(length(engine_paths), length(golden$paths),
    info = paste0(label, ": path count"))
  for (grow in golden$paths) {
    erow <- engine_paths[[grow$id]]
    expect_false(is.null(erow), info = paste0(label, ": missing path ", grow$id))
    expect_equal(as.numeric(erow$estimate), grow$estimate,
      tolerance = longitudinal_tolerance$estimate, info = paste0(label, ": est ", grow$id))
    expect_equal(as.numeric(erow$standardizedEstimate), grow$standardizedEstimate,
      tolerance = longitudinal_tolerance$estimate, info = paste0(label, ": std ", grow$id))
    expect_equal(as.numeric(erow$standardError), grow$standardError,
      tolerance = longitudinal_tolerance$se, info = paste0(label, ": se ", grow$id))
    expect_equal(as.numeric(erow$pValue), grow$pValue,
      tolerance = longitudinal_tolerance$estimate, info = paste0(label, ": p ", grow$id))
  }
  invisible(TRUE)
}

test_that("CLPM matches the direct lavaan fit on the synthetic panel", {
  skip_if(is.null(longitudinal_oracle) || !file.exists(panel_path),
    "longitudinal golden assets absent")
  data <- read.csv(panel_path, check.names = FALSE)
  result <- fit_longitudinal_panel(data, panel_spec("clpm"), function(id) id, 0.95)
  check_panel(result, longitudinal_oracle$clpm, "CLPM")
})

test_that("RI-CLPM matches the direct lavaan fit on the synthetic panel", {
  skip_if(is.null(longitudinal_oracle) || !file.exists(panel_path),
    "longitudinal golden assets absent")
  data <- read.csv(panel_path, check.names = FALSE)
  result <- fit_longitudinal_panel(data, panel_spec("ri_clpm"), function(id) id, 0.95)
  check_panel(result, longitudinal_oracle$riClpm, "RI-CLPM")
})
