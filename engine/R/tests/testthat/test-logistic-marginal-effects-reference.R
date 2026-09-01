source_engine("lib/runtime.R")
source_engine("lib/marginal_effects.R")
source_engine("lib/regression_reporting.R")

test_that("logistic AME and ADC match the independent marginaleffects oracle", {
  expect_true(requireNamespace("marginaleffects", quietly = TRUE))
  fixture_path <- file.path(
    project_root,
    "engine",
    "R",
    "tests",
    "reference",
    "logistic-marginal-effects-reference-v1.json"
  )
  expect_true(file.exists(fixture_path))
  fixture <- jsonlite::fromJSON(fixture_path, simplifyVector = FALSE)
  expect_identical(fixture$fixtureId, "logistic-marginal-effects-reference-v1")
  expect_identical(fixture$referenceImplementation, "marginaleffects")
  expect_identical(
    fixture$referenceVersion,
    as.character(packageVersion("marginaleffects"))
  )

  source_engine("tests/reference/logistic-marginal-effects-fixtures.R")
  reference_cases <- researchpath_logistic_oracle_cases()
  fixture_by_id <- setNames(fixture$cases, vapply(fixture$cases, function(case) case$caseId, character(1)))

  for (case in reference_cases) {
    expected <- fixture_by_id[[case$caseId]]
    expect_false(is.null(expected), info = case$caseId)
    data <- case$build()
    result <- fit_binary_logistic_with_ame(
      data,
      stats::as.formula(case$formulaText),
      identity,
      confidence_level = case$confidenceLevel
    )
    expected_terms <- expected$terms
    for (expected_term in expected_terms) {
      coefficient <- Filter(function(row) identical(row$term, expected_term$term), result$coefficients)[[1]]
      expect_equal(
        coefficient$averageMarginalEffect,
        as.numeric(expected_term$estimate),
        tolerance = fixture$tolerance$estimate,
        info = paste(case$caseId, expected_term$term, "estimate")
      )
      expect_equal(
        coefficient$marginalEffectStandardError,
        as.numeric(expected_term$standardError),
        tolerance = fixture$tolerance$standardError,
        info = paste(case$caseId, expected_term$term, "standard error")
      )
      expect_equal(
        coefficient$marginalEffectCiLower,
        as.numeric(expected_term$confidenceInterval$lower),
        tolerance = fixture$tolerance$confidenceInterval,
        info = paste(case$caseId, expected_term$term, "CI lower")
      )
      expect_equal(
        coefficient$marginalEffectCiUpper,
        as.numeric(expected_term$confidenceInterval$upper),
        tolerance = fixture$tolerance$confidenceInterval,
        info = paste(case$caseId, expected_term$term, "CI upper")
      )
    }
  }
})
