source_engine("lib/esem_bifactor.R")
source_engine("lib/cfa.R")

test_that("bifactor loading validator rejects zero-filled missing rows", {
  items <- paste0("item", 1:4)
  general <- setNames(c(0.7, NA_real_, 0.6, 0.5), items)
  specific <- matrix(
    c(0.4, 0.5, 0.3, 0.4, 0.1, 0.2, 0.1, 0.2),
    nrow = 4, byrow = FALSE
  )
  specific[1, ] <- NA_real_
  residuals <- setNames(c(0.5, 0.4, NA_real_, 0.3), items)

  error <- bifactor_loading_missing_error(general, specific, residuals)
  expect_match(error, "bifactor_loading_matrix_incomplete")
  expect_match(error, "item1")
  expect_match(error, "item3")

  complete_general <- setNames(c(0.7, 0.6, 0.5, 0.4), items)
  complete_residuals <- setNames(c(0.5, 0.4, 0.3, 0.2), items)
  complete_specific <- matrix(c(0.4, 0.5, 0.3, 0.4, 0.1, 0.2, 0.1, 0.2), nrow = 4)
  expect_null(bifactor_loading_missing_error(
    complete_general, complete_specific, complete_residuals
  ))
})

test_that("CFA post.check failures are reported as unknown, not positive definite", {
  expect_identical(cfa_positive_definiteness(TRUE), "positive_definite")
  expect_identical(cfa_positive_definiteness(FALSE), "not_positive_definite")
  expect_identical(cfa_positive_definiteness(NA), "unknown")
})
