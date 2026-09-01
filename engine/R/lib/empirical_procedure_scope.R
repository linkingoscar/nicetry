# A historical request without procedure keeps the bundle semantics. New UI
# requests always name one procedure. Dependencies are explicit, never inferred
# from unrelated configuration fields.
procedure <- options$procedure
requested <- function(name) is.null(procedure) || identical(procedure, name)
measurement_requested <- is.null(procedure) || procedure %in% c(
  "reliability", "efa", "cfa", "validity", "common_method", "invariance", "aggregation"
)
if (!is.null(procedure) && length(options$constructIds) > 0L) {
  metadata$constructs <- Filter(function(x) x$id %in% unlist(options$constructIds), metadata$constructs)
}
not_requested <- list(available = FALSE, reason = "not_requested")
common_method <- factorability <- cfa <- not_requested
efa <- c(not_requested, list(factorCount = 0L, factorLabels = list(), loadings = list()))
validity <- c(not_requested, list(constructs = list(), constructLabels = list()))
measurement_invariance <- not_requested
measurement_sample_adequacy <- NULL
passes_confirmatory_guardrail <- TRUE
estimated_parameter_count <- 0L
cases_per_parameter <- NA_real_
measurement_item_scale <- NULL
parallel_res <- parallel_fallback_reason <- kmo_skipped_reason <- NULL
factor_method <- "not_requested"
construct_validity <- list()
construct_score_ids <- character(0)
htmt_available <- FALSE
htmt_reason <- NULL
htmt_undefined_pairs <- list()
htmt_ci <- list(replicates = 0L, seed = options$randomSeed)
reliability <- NULL
