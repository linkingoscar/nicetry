source_engine("lib/seed_utils.R")

test_that("researchpath_seed preserves in-range integers", {
  expect_identical(researchpath_seed(20260714), 20260714L)
  expect_identical(researchpath_seed(42.0), 42L)
  expect_identical(researchpath_seed("20260714"), 20260714L)
})

test_that("researchpath_seed maps out-of-range seeds deterministically", {
  # as.integer() would overflow these to NA (set.seed(NA) errors) or truncate.
  big <- 2^40 + 12345
  first <- researchpath_seed(big)
  second <- researchpath_seed(big)
  expect_identical(first, second)
  expect_true(is.integer(first))
  expect_true(is.finite(first))
  expect_gt(first, 0L)
  # 2^31-1 is the largest set.seed-friendly positive integer.
  expect_lte(first, .Machine$integer.max)

  negative <- researchpath_seed(-1)
  expect_true(is.integer(negative) && is.finite(negative))
  expect_identical(negative, researchpath_seed(-1))
})

test_that("researchpath_seed handles NULL and invalid input with warning", {
  expect_identical(researchpath_seed(NULL), researchpath_seed_default)
  expect_warning(
    researchpath_seed("not-a-number"),
    "falling back to"
  )
  expect_identical(
    suppressWarnings(researchpath_seed("not-a-number")),
    researchpath_seed_default
  )
  expect_warning(researchpath_seed(Inf), "falling back to")
})

test_that("researchpath_seed salt derives stable chain seeds", {
  base <- 12345
  chain_a <- researchpath_seed(base, 1 * 1009L)
  chain_b <- researchpath_seed(base, 2 * 1009L)
  expect_identical(chain_a, researchpath_seed(base, 1 * 1009L))
  expect_identical(chain_b, researchpath_seed(base, 2 * 1009L))
  expect_false(identical(chain_a, chain_b))
  # Salt arithmetic beyond integer range still yields a valid seed.
  huge_salt <- 2^35
  expect_identical(
    researchpath_seed(base, huge_salt),
    researchpath_seed(base, huge_salt)
  )
  expect_true(is.finite(researchpath_seed(base, huge_salt)))
})

test_that("same seed reproduces the same RNG stream", {
  draw_once <- function(seed_value) {
    set.seed(researchpath_seed(seed_value))
    rnorm(5)
  }
  expect_identical(draw_once(2^40), draw_once(2^40))
  expect_false(identical(draw_once(2^40), draw_once(2^40 + 1)))
})
