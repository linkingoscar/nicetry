source_engine("lib/seed_utils.R")
source_engine("lib/runtime.R")
source_engine("lib/validity.R")
source_engine("lib/cfa_validity.R")

test_that("single-item constructs no longer report perfect CR/AVE", {
  item_frame <- data.frame(item1 = c(1, 2, 2, 3, 3, 3, 4, 4, 5, 5))
  constructs <- list(list(
    id = "construct_single",
    label = "Single",
    scoreId = "score_single",
    itemIds = list("item1"),
    alpha = NULL,
    omega = NULL
  ))
  result <- build_construct_validity(
    constructs,
    item_frame,
    list(available = FALSE, itemIds = list(), standardizedLoadings = list())
  )[[1]]

  expect_true(is.na(result$compositeReliability))
  expect_true(is.na(result$averageVarianceExtracted))
  expect_true(is.na(result$sqrtAve))
  expect_match(result$reliabilityWarning, "单题项构念")
})

test_that("Fornell-Larcker refuses an identity-matrix fallback", {
  cr_ave <- list(
    list(constructId = "a", sqrtAve = 0.7),
    list(constructId = "b", sqrtAve = 0.8)
  )
  result <- calc_fornell_larcker(cr_ave, factor_correlations = NULL)
  expect_false(result$available)
  expect_match(result$reason, "factor_correlations_unavailable")
  expect_identical(result$source, "unavailable")
  expect_true(all(vapply(result$constructEvaluations, function(row) {
    identical(row$status, "not_evaluable")
  }, logical(1))))
})
