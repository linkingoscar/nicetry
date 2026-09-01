source_engine("lib/diary_utils.R")
source_engine("lib/centering_utils.R")

test_that("person-mean centering uses equal person weights", {
  data <- data.frame(
    person = c("a", "a", "a", "b", "b"),
    x = c(1, 2, 3, 10, 10)
  )
  spec <- list(
    subjectVariableId = "person",
    predictorVariableId = "x",
    centering = "person_mean"
  )

  centered <- center_predictor(data, spec)

  expect_equal(as.numeric(centered$data$x__within), c(-1, 0, 1, 0, 0), tolerance = 1e-12)
  expect_equal(as.numeric(centered$data$x__between), c(-4, -4, -4, 4, 4), tolerance = 1e-12)
  expect_equal(centered$protocol$level2Reference, 6, tolerance = 1e-12)
  expect_identical(centered$protocol$grandMeanWeighting, "equal weight per person")
})

test_that("diary compatibility names resolve to the canonical functions", {
  source_engine("lib/diary_multilevel.R")

  expect_identical(diary_prepare, validate_diary_data)
  expect_identical(diary_center_predictor, center_predictor)
  expect_identical(diary_centering_manifest, centering_manifest)
  expect_identical(diary_finite, ensure_finite)
})
