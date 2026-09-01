source_engine("lib/seed_utils.R")
source_engine("lib/runtime.R")
source_engine("lib/efa.R")

test_that("ordinal empirical EFA fits from a polychoric matrix and never PCA-falls back", {
  set.seed(20260825)
  ordinal_items <- as.data.frame(lapply(1:6, function(index) {
    cut(rnorm(240), breaks = 5, labels = FALSE)
  }))
  names(ordinal_items) <- paste0("item", 1:6)
  correlation_matrix <- unclass(lavaan::lavCor(
    ordinal_items,
    ordered = names(ordinal_items)
  ))

  result <- fit_empirical_efa(
    ordinal_items,
    factor_count = 1,
    rotation = "varimax",
    correlation_matrix = correlation_matrix,
    sample_size = nrow(ordinal_items),
    allow_pca_fallback = FALSE
  )

  expect_true(isTRUE(result$available))
  expect_match(result$executedMethod, "_polychoric$")
  expect_false(result$fallbackApplied)
  expect_true(is.matrix(result$loadings))
})

test_that("a singular polychoric matrix is unavailable instead of falling back to Pearson PCA", {
  singular <- matrix(1, nrow = 5, ncol = 5)
  dimnames(singular) <- list(paste0("item", 1:5), paste0("item", 1:5))

  result <- fit_empirical_efa(
    data.frame(a = 1:5, b = 1:5, c = 1:5, d = 1:5, e = 1:5),
    factor_count = 1,
    rotation = "varimax",
    correlation_matrix = singular,
    sample_size = 50,
    allow_pca_fallback = FALSE
  )

  expect_false(isTRUE(result$available))
  expect_identical(result$executedMethod, "unavailable")
  expect_identical(result$fallbackCode, "EFA_FACTANAL_UNAVAILABLE_NO_PCA_FOR_ORDINAL")
  expect_match(result$reason, "ordinal_polychoric_efa_failed")
})
