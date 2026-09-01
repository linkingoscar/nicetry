write_sem_failure <- function(code, reason) {
  first_order_ids <- vapply(
    Filter(function(latent) !identical(latent$level, "higher_order"), spec$latents),
    function(latent) latent$id,
    character(1)
  )
  higher_order_ids <- vapply(
    Filter(function(latent) identical(latent$level, "higher_order"), spec$latents),
    function(latent) latent$id,
    character(1)
  )
  sem_failure_reasons <- as.list(c(code))
  fallback_result <- list(
    schemaVersion = "0.3.0",
    run = list(
      id = payload$runId, status = "succeeded", modelId = spec$modelId,
      modelHash = payload$modelHash,
      modelVersionId = if (is.null(payload$modelVersionId)) "demo" else payload$modelVersionId,
      template = "sem", durationMilliseconds = as.integer((proc.time()[[3]] - started_at) * 1000)
    ),
    sampleFlow = list(
      original = original_n, selected = original_n, included = included_n,
      excluded = original_n - included_n, missingRows = original_n - included_n,
      finalN = included_n, missingMethod = spec$estimation$missing,
      variableMissingCounts = variable_missing_counts,
      missingPatterns = missing_patterns
    ),
    equations = list(), diagnostics = list(), effects = list(), probes = list(), johnsonNeyman = NULL,
    moderator = NULL,
    semResult = list(
      fitIndices = list(
        chiSquare = NULL, df = NULL, pValue = NULL, cfi = NULL, tli = NULL, rmsea = NULL,
        srmr = NULL, rmseaCiLower = NULL, rmseaCiUpper = NULL
      ),
      loadings = list(), paths = list(), reliability = list(),
      modelStructure = list(firstOrderLatents = as.list(first_order_ids), higherOrderLatents = as.list(higher_order_ids)),
      publicationEligible = FALSE, requiresManualReview = TRUE,
      publicationEligibilityReasons = sem_failure_reasons,
      numericReferenceMatrix = list(
        failureStates = list(
          heywood = "publicationEligible=false; requiresManualReview=true",
          nonPositiveDefinite = "publicationEligible=false; requiresManualReview=true",
          nonConvergence = "execution failed; no inferential results published"
        )
      )
    ),
    invarianceResult = NULL,
    publicationEligible = FALSE, requiresManualReview = TRUE,
    publicationEligibilityReasons = sem_failure_reasons,
    claimBoundary = list(
      claimMode = "association", causalLanguageAllowed = FALSE,
      temporalPrecedenceEstablished = FALSE, experimentalEffectEstablished = FALSE
    ),
    warnings = list(list(code = code, severity = "error", message = reason)),
    provenance = list(
      engine = "researchpath-r", engineVersion = "0.3.0", rVersion = R.version.string,
      jsonliteVersion = as.character(packageVersion("jsonlite")), dataSha256 = payload$dataSha256,
      standardErrors = "standard", confidenceLevel = spec$estimation$confidenceLevel,
      estimator = estimator, missingMethodExecuted = missing_param,
      bootstrapReplicates = 0L, seed = 12345L
    )
  )
  researchpath_write_result(fallback_result, output_path)
  write_progress("succeeded", 1.0, 0L, 0L)
  q(save = "no")
}
