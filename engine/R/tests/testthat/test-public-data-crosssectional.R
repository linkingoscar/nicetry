# Public-data cross-sectional validation: the empirical workspace's
# hierarchical regression and group comparison vs base R textbook oracles on
# Hayes' glbwarm data.
#
# The oracle (engine/R/tests/reference/public-data-crosssectional.json) is
# computed with base R lm/anova/t.test/aov/TukeyHSD and textbook effect-size
# formulas; the engine runs the same models through
# fit_hierarchical_regression / fit_empirical_group_comparison. Tolerances
# are tight (same base-R estimators), not statistical.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
public_data_dir <- Sys.getenv(
  "RESEARCHPATH_PUBLIC_DATA_DIR",
  file.path(project_root, "output", "validation-datasets")
)
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "public-data-crosssectional.json")
data_path <- file.path(public_data_dir, "hayes", "hayes2022data", "glbwarm", "glbwarm.csv")

source_engine <- function(relative_path) {
  source(file.path(project_root, "engine", "R", relative_path), local = globalenv())
}

cross_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
cross_tolerance <- cross_oracle$provenance$tolerance
label_for <- function(id) id

source_engine("lib/runtime.R")
source_engine("lib/inference_covariance.R")
source_engine("lib/regression_reporting.R")
source_engine("lib/relative_importance.R")
source_engine("lib/hierarchical_regression.R")
source_engine("lib/empirical_group_reporting.R")

test_that("hierarchical regression matches base R lm on glbwarm", {
  skip_if(!file.exists(data_path) || is.null(cross_oracle),
    "public cross-sectional validation assets absent")
  data <- read.csv(data_path, check.names = FALSE)
  options <- list(
    outcomeVariableId = "govact",
    controlVariableIds = c("posemot", "ideology", "sex"),
    predictorVariableIds = c("negemot"),
    groupOmnibusPAdjust = "none"
  )
  result <- fit_hierarchical_regression(data, options, label_for, 0.95, "public_xs")
  golden <- cross_oracle$hierarchical

  expect_equal(result$n, golden$n, info = "regression complete-case N")
  expect_false(isTRUE(result$underdetermined), info = "regression must not be underdetermined")

  for (block_index in c(1L, 2L)) {
    engine_block <- result$blocks[[block_index]]
    golden_block <- if (block_index == 1L) golden$block1 else golden$block2
    expect_equal(as.numeric(engine_block$rSquared), golden_block$rSquared,
      tolerance = cross_tolerance$rSquared, info = paste0("block ", block_index, " R2"))
    engine_by_term <- stats::setNames(engine_block$coefficients,
      vapply(engine_block$coefficients, `[[`, character(1), "term"))
    for (row in golden_block$coefficients) {
      engine_row <- engine_by_term[[row$term]]
      expect_false(is.null(engine_row), info = paste0("block ", block_index, " term ", row$term))
      expect_equal(as.numeric(engine_row$estimate), row$estimate,
        tolerance = cross_tolerance$estimate, info = paste0("block ", block_index, " est ", row$term))
      expect_equal(as.numeric(engine_row$standardError), row$standardError,
        tolerance = cross_tolerance$se, info = paste0("block ", block_index, " se ", row$term))
      expect_equal(as.numeric(engine_row$pValue), row$pValue,
        tolerance = cross_tolerance$pValue, info = paste0("block ", block_index, " p ", row$term))
    }
  }

  change <- result$change
  expect_equal(as.numeric(change$deltaRSquared), golden$change$deltaRSquared,
    tolerance = cross_tolerance$rSquared, info = "delta R2")
  expect_equal(as.numeric(change$statistic), golden$change$statistic,
    tolerance = cross_tolerance$statistic, info = "F change")
  expect_equal(as.numeric(change$df1), golden$change$df1, info = "F change df1")
  expect_equal(as.numeric(change$df2), golden$change$df2, info = "F change df2")
  expect_equal(as.numeric(change$pValue), golden$change$pValue,
    tolerance = cross_tolerance$pValue, info = "F change p")
})

test_that("two-group comparison (Welch t + Hedges g) matches base R on glbwarm", {
  skip_if(!file.exists(data_path) || is.null(cross_oracle),
    "public cross-sectional validation assets absent")
  data <- read.csv(data_path, check.names = FALSE)
  options <- list(groupVariableId = "sex", groupOmnibusPAdjust = "none")
  result <- fit_empirical_group_comparison(
    data, options, c("govact"), label_for, finite_number, FALSE, 0.95, "public_xs"
  )
  row <- result$results[[1]]
  golden <- cross_oracle$group2

  expect_equal(as.numeric(row$statistic), golden$statistic,
    tolerance = cross_tolerance$statistic, info = "Welch t statistic")
  expect_equal(as.numeric(row$df1), golden$df,
    tolerance = 1e-6, info = "Welch t df")
  expect_equal(as.numeric(row$pValue), golden$pValue,
    tolerance = cross_tolerance$pValue, info = "Welch t p")
  expect_equal(as.numeric(row$effectSize), golden$effectSize,
    tolerance = cross_tolerance$effectSize, info = "Hedges g")
  expect_equal(as.numeric(row$effectSizeCiLower), golden$effectSizeCiLower,
    tolerance = cross_tolerance$effectSize, info = "Hedges g CI lower")
  expect_equal(as.numeric(row$effectSizeCiUpper), golden$effectSizeCiUpper,
    tolerance = cross_tolerance$effectSize, info = "Hedges g CI upper")
  for (index in seq_along(golden$groups)) {
    engine_group <- row$groups[[index]]
    golden_group <- golden$groups[[index]]
    expect_equal(as.numeric(engine_group$n), golden_group$n, info = paste0("group ", index, " n"))
    expect_equal(as.numeric(engine_group$mean), golden_group$mean,
      tolerance = cross_tolerance$groupSummary, info = paste0("group ", index, " mean"))
    expect_equal(as.numeric(engine_group$sd), golden_group$sd,
      tolerance = cross_tolerance$groupSummary, info = paste0("group ", index, " sd"))
  }
})

test_that("three-group comparison (ANOVA + omega2 + post hoc) matches base R on glbwarm", {
  skip_if(!file.exists(data_path) || is.null(cross_oracle),
    "public cross-sectional validation assets absent")
  data <- read.csv(data_path, check.names = FALSE)
  options <- list(groupVariableId = "partyid", groupOmnibusPAdjust = "none")
  result <- fit_empirical_group_comparison(
    data, options, c("govact"), label_for, finite_number, FALSE, 0.95, "public_xs"
  )
  row <- result$results[[1]]
  golden <- cross_oracle$group3

  expect_equal(as.numeric(row$statistic), golden$statistic,
    tolerance = cross_tolerance$statistic, info = "ANOVA F")
  expect_equal(as.numeric(row$df1), golden$df1, info = "ANOVA df1")
  expect_equal(as.numeric(row$df2), golden$df2, info = "ANOVA df2")
  expect_equal(as.numeric(row$pValue), golden$pValue,
    tolerance = cross_tolerance$pValue, info = "ANOVA p")
  expect_equal(as.numeric(row$effectSize), golden$etaSquared,
    tolerance = cross_tolerance$effectSize, info = "eta squared")
  expect_equal(as.numeric(row$omegaSquared), golden$omegaSquared,
    tolerance = cross_tolerance$effectSize, info = "omega squared")

  bf <- row$assumptionTests$brownForsythe
  expect_equal(as.numeric(bf$statistic), golden$brownForsythe$statistic,
    tolerance = cross_tolerance$statistic, info = "Brown-Forsythe F")
  expect_equal(as.numeric(bf$pValue), golden$brownForsythe$pValue,
    tolerance = cross_tolerance$pValue, info = "Brown-Forsythe p")

  welch <- row$robustTest
  expect_equal(as.numeric(welch$statistic), golden$welch$statistic,
    tolerance = cross_tolerance$statistic, info = "Welch one-way F")
  expect_equal(as.numeric(welch$pValue), golden$welch$pValue,
    tolerance = cross_tolerance$pValue, info = "Welch one-way p")

  engine_tukey <- stats::setNames(row$pairwiseTukey,
    vapply(row$pairwiseTukey, `[[`, character(1), "comparison"))
  for (grow in golden$tukey) {
    erow <- engine_tukey[[grow$comparison]]
    expect_false(is.null(erow), info = paste0("tukey row ", grow$comparison))
    expect_equal(as.numeric(erow$difference), grow$difference,
      tolerance = cross_tolerance$estimate, info = paste0("tukey diff ", grow$comparison))
    expect_equal(as.numeric(erow$pValue), grow$pValue,
      tolerance = cross_tolerance$pValue, info = paste0("tukey p ", grow$comparison))
  }

  engine_gh <- stats::setNames(row$pairwiseGamesHowell,
    vapply(row$pairwiseGamesHowell, `[[`, character(1), "comparison"))
  for (grow in golden$gamesHowell) {
    erow <- engine_gh[[grow$comparison]]
    expect_false(is.null(erow), info = paste0("games-howell row ", grow$comparison))
    expect_equal(as.numeric(erow$difference), grow$difference,
      tolerance = cross_tolerance$estimate, info = paste0("GH diff ", grow$comparison))
    expect_equal(as.numeric(erow$standardError), grow$standardError,
      tolerance = cross_tolerance$se, info = paste0("GH se ", grow$comparison))
    expect_equal(as.numeric(erow$pValue), grow$pValue,
      tolerance = cross_tolerance$pValue, info = paste0("GH p ", grow$comparison))
  }
})
