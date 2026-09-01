source_engine("lib/runtime.R")
source_engine("lib/validity.R")
source_engine("lib/inference_covariance.R")
source_engine("lib/regression_reporting.R")
source_engine("lib/bootstrap.R")
source_engine("lib/empirical_group_reporting.R")
source_engine("lib/experimental_cluster_glm.R")

expect_metamorphic <- function(condition, property, counterexample) {
  if (!isTRUE(condition)) {
    artifact <- file.path(
      tempdir(),
      paste0("researchpath-counterexample-", gsub("[^a-z0-9]+", "-", tolower(property)), ".json")
    )
    jsonlite::write_json(
      list(property = property, counterexample = counterexample),
      artifact,
      auto_unbox = TRUE,
      pretty = TRUE,
      na = "null"
    )
    fail(paste0(property, " failed; minimized deterministic counterexample: ", artifact))
  }
  succeed()
}

metamorphic_fixture <- function() {
  set.seed(20260824)
  n <- 180
  x <- rnorm(n)
  z <- rnorm(n)
  group <- factor(rep(c("A", "B", "C"), each = n / 3))
  y <- 0.6 * x - 0.25 * z + c(A = 0, B = 0.4, C = -0.25)[group] + rnorm(n, sd = 0.8)
  data.frame(y = y, x = x, z = z, group = group)
}

test_that("regression and correlation survive row permutation and variable renaming", {
  data <- metamorphic_fixture()
  permutation <- sample.int(nrow(data))
  original_fit <- lm(y ~ x + z, data = data)
  permuted_fit <- lm(y ~ x + z, data = data[permutation, , drop = FALSE])
  original_rows <- coefficient_rows(original_fit, identity, confidence_level = 0.90)
  permuted_rows <- coefficient_rows(permuted_fit, identity, confidence_level = 0.90)
  original_values <- vapply(original_rows, `[[`, numeric(1), "estimate")
  permuted_values <- vapply(permuted_rows, `[[`, numeric(1), "estimate")
  expect_metamorphic(
    isTRUE(all.equal(original_values, permuted_values, tolerance = 1e-12)),
    "row permutation preserves OLS estimates",
    list(permutation = permutation)
  )

  renamed <- setNames(data[c("y", "x", "z")], c("outcome", "predictor", "control"))
  renamed_fit <- lm(outcome ~ predictor + control, data = renamed)
  expect_metamorphic(
    isTRUE(all.equal(unname(coef(original_fit)), unname(coef(renamed_fit)), tolerance = 1e-12)),
    "variable renaming preserves OLS estimates",
    list(original = names(data), renamed = names(renamed))
  )

  original_cor <- calc_correlation_matrix_with_ci(data[c("x", "y", "z")], confidence_level = 0.90)
  permuted_cor <- calc_correlation_matrix_with_ci(
    data[permutation, c("x", "y", "z")], confidence_level = 0.90
  )
  expect_metamorphic(
    isTRUE(all.equal(original_cor, permuted_cor, tolerance = 1e-12)),
    "row permutation preserves correlation bundle",
    list(permutation = permutation)
  )
})

test_that("translation and scale transformations obey the declared OLS mapping", {
  data <- metamorphic_fixture()
  original <- lm(y ~ x + z, data = data)
  transformed <- transform(data, x = 3 * x + 7, y = -2 * y + 5)
  changed <- lm(y ~ x + z, data = transformed)
  expected_x <- -2 * coef(original)[["x"]] / 3
  expected_z <- -2 * coef(original)[["z"]]
  expect_metamorphic(
    isTRUE(all.equal(coef(changed)[["x"]], expected_x, tolerance = 1e-12)) &&
      isTRUE(all.equal(coef(changed)[["z"]], expected_z, tolerance = 1e-12)),
    "OLS scale and translation equivariance",
    list(xScale = 3, xShift = 7, yScale = -2, yShift = 5)
  )
})

test_that("factor reference changes parameterization but not fitted values", {
  data <- metamorphic_fixture()
  reference_a <- lm(y ~ group + x, data = data)
  data$group <- stats::relevel(data$group, ref = "B")
  reference_b <- lm(y ~ group + x, data = data)
  expect_metamorphic(
    isTRUE(all.equal(fitted(reference_a), fitted(reference_b), tolerance = 1e-12)),
    "factor reference preserves fitted values",
    list(firstReference = "A", secondReference = "B")
  )
})

cluster_fixture <- function() {
  set.seed(20260825)
  clusters <- factor(rep(sprintf("c%02d", 1:12), each = 8))
  cluster_effect <- rep(rnorm(12, sd = 1.4), each = 8)
  x <- rnorm(length(clusters))
  data.frame(y = 0.75 * x + cluster_effect + rnorm(length(x), sd = 0.35), x = x, cluster = clusters)
}

run_cluster_fixture <- function(data, confidence_level = 0.90) {
  assign("spec", list(
    outcomeIds = list("y"), betweenFactors = list(), covariateIds = list("x"),
    clusterVariableId = "cluster", confidenceLevel = confidence_level
  ), envir = globalenv())
  assign("family", "experimental_design", envir = globalenv())
  assign("read_analysis_data", function() data, envir = globalenv())
  run_cluster_glm()
}

test_that("cluster label permutation preserves CR0 inference and sample flow", {
  data <- cluster_fixture()
  original <- run_cluster_fixture(data)
  renamed <- data
  label_map <- setNames(rev(levels(data$cluster)), levels(data$cluster))
  renamed$cluster <- factor(unname(label_map[as.character(data$cluster)]))
  relabelled <- run_cluster_fixture(renamed)
  original_rows <- original$familyResult$coefficients
  renamed_rows <- relabelled$familyResult$coefficients
  fields <- c("estimate", "standardError", "statistic", "pValue", "confidenceLower", "confidenceUpper")
  for (field in fields) {
    expect_equal(
      vapply(original_rows, `[[`, numeric(1), field),
      vapply(renamed_rows, `[[`, numeric(1), field),
      tolerance = 1e-12
    )
  }
  flow <- original$sampleFlow
  expect_metamorphic(
    identical(flow$original, flow$included + flow$excluded) && flow$clusters == 12,
    "sample flow conserves rows and clusters",
    flow
  )
})

test_that("named statistical mutants are killed by product invariants", {
  data <- cluster_fixture()
  cluster_result <- run_cluster_fixture(data, confidence_level = 0.90)
  product_row <- cluster_result$familyResult$coefficients[[2]]
  naive_row <- summary(lm(y ~ x, data = data))$coefficients[2, ]

  assign("replicates", 200L, envir = globalenv())
  assign("alpha", 0.10, envir = globalenv())
  assign("bootstrap_config", list(method = "bias_corrected"), envir = globalenv())
  bootstrap_result <- bootstrap_ci(seq(-1, 1, length.out = 200), original_estimate = 0.25)

  group_data <- metamorphic_fixture()
  group_result <- fit_empirical_group_comparison(
    group_data,
    list(groupVariableId = "group", groupOmnibusPAdjust = "holm"),
    c("y", "z"),
    identity,
    finite_number,
    FALSE,
    confidence_level = 0.90
  )
  raw <- vapply(group_result$results, `[[`, numeric(1), "pValueRaw")
  adjusted <- vapply(group_result$results, `[[`, numeric(1), "pValueAdjusted")
  displayed <- vapply(group_result$results, `[[`, numeric(1), "pValue")

  mutant_kills <- c(
    fixed_1_96 = abs(cluster_glm_two_sided_critical(0.90, 11) - 1.96) > 0.05,
    wrong_residual_df = product_row$degreesOfFreedom == 11 && product_row$degreesOfFreedom != 94,
    ignore_cluster = abs(product_row$standardError - naive_row[["Std. Error"]]) > 1e-3,
    mislabel_bc_as_bca = identical(bootstrap_result$method, "bootstrap_bias_corrected") &&
      !identical(bootstrap_result$method, "bootstrap_bca"),
    drop_structured_warning = length(cluster_result$warnings) > 0L &&
      identical(cluster_result$warnings[[1]]$code, "GLM_CLUSTER_SMALL_CLUSTER_COUNT"),
    swap_raw_and_adjusted_p = any(abs(raw - adjusted) > 1e-12) &&
      all(adjusted >= raw) && isTRUE(all.equal(displayed, adjusted, tolerance = 0))
  )
  expect_metamorphic(
    all(mutant_kills),
    "all named statistical mutants are killed",
    list(killed = as.list(mutant_kills), survivors = names(mutant_kills)[!mutant_kills])
  )
})
