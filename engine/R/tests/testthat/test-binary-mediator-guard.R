source_engine("lib/seed_utils.R")
source_engine("lib/process5_standard.R")

process_node <- function(id, role, data_type, encoding = NULL) {
  node <- list(
    id = id, variableId = paste0("var_", id), label = toupper(id),
    kind = "observed", role = role, dataType = data_type
  )
  if (!is.null(encoding)) node$encoding <- encoding
  node
}

test_that("PROCESS guard rejects a binary mediator before estimation", {
  spec <- list(
    nodes = list(
      process_node("x", "x", "continuous"),
      process_node("m", "m", "binary", list(method = "binary_indicator")),
      process_node("y", "y", "continuous")
    ),
    edges = list()
  )

  guard <- process5_standard_guard(spec, 4)

  expect_false(guard$valid)
  expect_true(any(grepl("BINARY_MEDIATOR_NOT_SUPPORTED", guard$errors, fixed = TRUE)))
})

test_that("PROCESS guard keeps the supported binary outcome path", {
  spec <- list(
    nodes = list(
      process_node("x", "x", "continuous"),
      process_node("m", "m", "continuous"),
      process_node("y", "y", "binary", list(method = "binary_indicator"))
    ),
    edges = list()
  )

  guard <- process5_standard_guard(spec, 4)

  expect_true(guard$valid)
  expect_false(any(grepl("BINARY_MEDIATOR_NOT_SUPPORTED", guard$errors, fixed = TRUE)))
})
