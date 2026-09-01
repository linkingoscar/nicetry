source_engine("lib/runtime.R")
source_engine("lib/esem_bifactor.R")

build_dif_data <- function(seed = 20260806L, n_per_group = 30L) {
  set.seed(seed)
  n <- n_per_group * 2L
  theta <- rnorm(n)
  group <- rep(c("A", "B"), each = n_per_group)
  prob_1pl <- function(b, a = 1.2, offset = 0) {
    p <- 1 / (1 + exp(-a * (theta - b))) + offset
    pmin(pmax(p, 0), 1)
  }
  data.frame(
    item1 = rbinom(n, 1, prob_1pl(-0.6)),
    item2 = rbinom(n, 1, prob_1pl(0.0)),
    item3 = rbinom(n, 1, prob_1pl(0.6)),
    item4 = rbinom(n, 1, prob_1pl(0.0, offset = ifelse(group == "B", 0.35, 0)))
  )
}

constructs <- list(
  list(id = "c1", label = "C1", itemIds = c("item1", "item2")),
  list(id = "c2", label = "C2", itemIds = c("item3", "item4"))
)

test_that("DIF analysis applies Holm correction across items", {
  skip_if_not_installed("mirt")
  items <- build_dif_data()
  group <- rep(c("A", "B"), each = 30L)
  result <- fit_irt_dif_model(items, constructs, group)

  expect_true(result$available)
  expect_length(result$difAnalysis, 4L)
  expect_identical(result$difAdjustmentMethod, "holm")
  expect_true(all(vapply(result$difAnalysis, function(entry) "pValueAdjusted" %in% names(entry), logical(1))))

  raw_p <- vapply(result$difAnalysis, function(entry) entry$pValue, numeric(1))
  actual_adjusted <- vapply(result$difAnalysis, function(entry) entry$pValueAdjusted, numeric(1))
  expect_equal(actual_adjusted, stats::p.adjust(raw_p, method = "holm"))

  detected <- vapply(result$difAnalysis, function(entry) entry$difDetected, logical(1))
  expect_identical(
    detected,
    !is.na(actual_adjusted) & actual_adjusted < 0.05
  )
})

test_that("DIF analysis without a group variable reports no adjustment", {
  skip_if_not_installed("mirt")
  items <- build_dif_data()
  result <- fit_irt_dif_model(items, constructs, group_variable = NULL)

  expect_true(result$available)
  expect_identical(result$difAdjustmentMethod, "none")
  expect_length(result$difAnalysis, 0L)
})
