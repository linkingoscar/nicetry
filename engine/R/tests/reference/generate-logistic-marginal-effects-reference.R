# Independent logistic marginal-effects oracle.
#
# The generator fits deterministic data directly with glm() and obtains
# marginal effects from marginaleffects. It never sources the ResearchPath
# estimator, so regenerating this fixture cannot mask a product regression.

suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(marginaleffects))

args <- commandArgs(trailingOnly = TRUE)
script_dir <- dirname(normalizePath(substring(grep("--file=", commandArgs(trailingOnly = FALSE), value = TRUE)[1], 8)))
source(file.path(script_dir, "logistic-marginal-effects-fixtures.R"), encoding = "UTF-8")

output_path <- if (length(args) >= 1L && nzchar(args[[1]])) {
  args[[1]]
} else {
  file.path(script_dir, "logistic-marginal-effects-reference-v1.json")
}

tolerance <- list(
  estimate = 1e-8,
  standardError = 1e-7,
  confidenceInterval = 1e-7
)

extract_row <- function(row, case, index) {
  product_term <- case$targetTerms[[min(index, length(case$targetTerms))]]
  contrast <- if ("contrast" %in% names(row)) as.character(row$contrast[[1]]) else NULL
  list(
    term = product_term,
    contrast = contrast,
    estimate = as.numeric(row$estimate[[1]]),
    standardError = as.numeric(row$std.error[[1]]),
    confidenceLevel = case$confidenceLevel,
    confidenceInterval = list(
      level = case$confidenceLevel,
      lower = as.numeric(row$conf.low[[1]]),
      upper = as.numeric(row$conf.high[[1]]),
      method = "marginaleffects_delta_method"
    )
  )
}

cases <- lapply(researchpath_logistic_oracle_cases(), function(case) {
  oracle <- researchpath_logistic_oracle_call(case)
  result <- oracle$result
  terms <- lapply(seq_len(nrow(result)), function(index) {
    extract_row(result[index, , drop = FALSE], case, index)
  })
  list(
    caseId = case$caseId,
    formula = case$formulaText,
    method = case$method,
    confidenceLevel = case$confidenceLevel,
    terms = terms
  )
})

fixture <- list(
  fixtureId = "logistic-marginal-effects-reference-v1",
  referenceImplementation = "marginaleffects",
  referenceVersion = as.character(packageVersion("marginaleffects")),
  referenceSource = "CRAN",
  referenceSourceUrl = "https://cran.r-project.org/package=marginaleffects",
  seed = 12345,
  covariance = "stats::vcov.glm (model default)",
  uncertainty = "delta_method_normal",
  tolerance = tolerance,
  cases = cases
)

dir.create(dirname(output_path), recursive = TRUE, showWarnings = FALSE)
jsonlite::write_json(
  fixture,
  path = output_path,
  pretty = TRUE,
  auto_unbox = TRUE,
  digits = NA,
  na = "null",
  null = "null"
)
cat(sprintf("Wrote %s (marginaleffects %s)\n", output_path, fixture$referenceVersion))
