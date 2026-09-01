source_engine("lib/invariance.R")

test_that("invariance availability exposes failed post-configural levels", {
  result <- invariance_model_availability(list(
    configural = list(chiSquare = 10),
    metric = NULL,
    scalar = list(chiSquare = 20),
    strict = NULL
  ))

  expect_true(result$modelAvailability$configural)
  expect_false(result$modelAvailability$metric)
  expect_true(result$modelAvailability$scalar)
  expect_false(result$modelAvailability$strict)
  expect_true(any(vapply(result$warnings, function(warning) {
    identical(warning$code, "INVARIANCE_LEVEL_UNAVAILABLE")
  }, logical(1))))
})
