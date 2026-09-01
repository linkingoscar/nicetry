# Shared semantics for marginal-effect reporting.

researchpath_declared_interaction_terms <- function(moderations) {
  if (is.null(moderations) || length(moderations) == 0L) return(character(0))
  terms <- unlist(lapply(moderations, function(moderation) {
    unlist(moderation[c("productTermId", "moderatorProductTermId")], use.names = FALSE)
  }), use.names = FALSE)
  unique(as.character(terms[!is.na(terms) & nzchar(as.character(terms))]))
}

researchpath_is_interaction_term <- function(
  term,
  declared_interaction_terms = character(0),
  term_labels = character(0)
) {
  term <- as.character(term)
  declared_interaction_terms <- as.character(declared_interaction_terms)
  term %in% declared_interaction_terms ||
    grepl(":", term, fixed = TRUE) ||
    any(vapply(term_labels, function(label) {
      nzchar(label) && grepl(":", label, fixed = TRUE) && startsWith(term, label)
    }, logical(1)))
}

researchpath_not_applicable_interaction_effect <- function(confidence_level = 0.95) {
  list(
    estimate = NA_real_,
    type = "not_applicable_interaction_term",
    estimand = "No ordinary AME is defined for a raw interaction/product term.",
    reason = "Use conditional effect or probe output for interaction interpretation.",
    referenceLevel = NULL,
    contrastLevel = NULL,
    standardError = NA_real_,
    ciLower = NA_real_,
    ciUpper = NA_real_,
    confidenceInterval = list(
      level = confidence_level,
      lower = NA_real_,
      upper = NA_real_,
      method = "not_applicable_interaction_term"
    )
  )
}
