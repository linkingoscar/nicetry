# Deterministic, reproducible seed normalization.
#
# R's set.seed() accepts integers in [-2^31, 2^31). Direct as.integer()
# coercion of out-of-range numeric seeds silently truncates (or yields NA,
# which makes set.seed(NA) an error), silently breaking the product promise
# that "the same data, spec, version and seed reproduce the same result".
#
# Every seed entering the engine flows through researchpath_seed() so that
# any finite numeric (or numeric-string) seed maps to the same integer on
# every run, on every platform. Derived seeds (chains, replicates) add a
# stable salt instead of arithmetic that can overflow.
#
# Fallback semantics: NULL/empty or non-finite input falls back to
# researchpath_seed_default with an explicit warning (product principle:
# every fallback must be visible, never silent).

researchpath_seed_default <- 20260807L

researchpath_seed <- function(seed, salt = 0) {
  if (is.null(seed) || length(seed) == 0L) {
    return(researchpath_seed_default)
  }
  numeric_value <- suppressWarnings(as.numeric(seed))
  if (length(numeric_value) != 1L || !is.finite(numeric_value)) {
    warning(
      "researchpath_seed: invalid seed '", paste(seed, collapse = ","),
      "', falling back to ", researchpath_seed_default,
      call. = FALSE
    )
    return(researchpath_seed_default)
  }
  normalized <- (numeric_value + as.numeric(salt)) %% .Machine$integer.max
  normalized <- floor(normalized)
  if (normalized < 1) normalized <- normalized + .Machine$integer.max
  as.integer(normalized)
}
