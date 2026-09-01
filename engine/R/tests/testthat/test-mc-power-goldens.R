# Golden test: Monte Carlo power vs an independent simulator.
#
# Two agreement rules, both frozen in mc-power-goldens-v1.json:
#  - same seed: achievedPower must match the oracle exactly (1e-9) — validates
#    the DGP implementation and RNG plumbing;
#  - different seeds: powers must agree within
#    3 * sqrt(mcse_engine^2 + mcse_oracle^2) — a statistical consistency bound
#    (~0.3% false-rejection rate), NOT a numerical tolerance.

project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
oracle_path <- file.path(project_root, "engine", "R", "tests", "reference",
  "mc-power-goldens-v1.json")

mc_oracle <- if (file.exists(oracle_path)) {
  jsonlite::fromJSON(oracle_path, simplifyVector = FALSE)
} else {
  NULL
}
mc_tolerance <- mc_oracle$provenance$tolerance

run_engine_mc <- function(case, seed, work_dir) {
  spec <- case$spec
  spec$family <- "power_analysis"
  spec$method <- "monte_carlo"
  spec$confidenceLevel <- 0.95
  spec$seed <- seed
  spec$datasetVersionId <- "mc_golden_v1"
  input_path <- file.path(work_dir, "input.json")
  output_path <- file.path(work_dir, "output.json")
  writeLines(
    jsonlite::toJSON(list(
      spec = spec,
      progressPath = file.path(work_dir, "progress.json"),
      cancelPath = file.path(work_dir, "cancel.json")
    ), auto_unbox = TRUE, digits = NA),
    input_path
  )
  runner <- file.path(project_root, "engine", "R", "run_advanced_analysis.R")
  rscript <- file.path(R.home("bin"), "Rscript.exe")
  status <- system2(
    rscript, c("--vanilla", shQuote(runner), shQuote(input_path), shQuote(output_path)),
    stdout = TRUE, stderr = TRUE
  )
  if (!file.exists(output_path)) {
    stop("run_advanced_analysis.R MC failed for ", case$spec$designFamily, ": ",
      paste(status, collapse = "\n"))
  }
  jsonlite::fromJSON(output_path, simplifyVector = FALSE)
}

expect_power_matches <- function(engine_result, reference, label, exact) {
  family_result <- engine_result$familyResult
  if (exact) {
    expect_equal(as.numeric(family_result$achievedPower), reference$power,
      tolerance = mc_tolerance$exact, info = paste0(label, ": exact achieved power"))
  } else {
    bound <- mc_tolerance$mcseBoundMultiplier * sqrt(
      as.numeric(family_result$monteCarloStandardError)^2 + reference$mcse^2
    )
    expect_true(
      abs(as.numeric(family_result$achievedPower) - reference$power) <= bound,
      info = paste0(label, ": power difference within 3*MCSE bound (engine=",
        as.numeric(family_result$achievedPower), ", oracle=", reference$power,
        ", bound=", bound, ")")
    )
  }
  # reported MCSE must equal the Bernoulli formula from its own power
  p <- as.numeric(family_result$achievedPower)
  expected_mcse <- sqrt(p * (1 - p) / as.numeric(family_result$validSimulations))
  expect_equal(as.numeric(family_result$monteCarloStandardError), expected_mcse,
    tolerance = 1e-9, info = paste0(label, ": MCSE formula"))
  expect_equal(as.numeric(family_result$simulationCount), 5000,
    info = paste0(label, ": simulation count"))
  expect_equal(as.numeric(family_result$failureCount), 0,
    info = paste0(label, ": no convergence failures"))
}

test_that("regression Monte Carlo power matches the independent simulator (exact seed)", {
  skip_if(is.null(mc_oracle), "MC golden assets absent")
  work <- tempfile("rp-mc-reg-exact-"); dir.create(work)
  result <- run_engine_mc(mc_oracle$regression, 20260816, work)
  expect_power_matches(result, mc_oracle$regression$exactRef, "regression exact", TRUE)
})

test_that("regression Monte Carlo power agrees within the MCSE bound (different seed)", {
  skip_if(is.null(mc_oracle), "MC golden assets absent")
  work <- tempfile("rp-mc-reg-stat-"); dir.create(work)
  result <- run_engine_mc(mc_oracle$regression, 20260814, work)
  expect_power_matches(result, mc_oracle$regression$statRef, "regression stat", FALSE)
})

test_that("ANOVA Monte Carlo power agrees within the MCSE bound (different seed)", {
  skip_if(is.null(mc_oracle), "MC golden assets absent")
  work <- tempfile("rp-mc-anova-stat-"); dir.create(work)
  result <- run_engine_mc(mc_oracle$anova, 20260814, work)
  expect_power_matches(result, mc_oracle$anova$statRef, "anova stat", FALSE)
})
