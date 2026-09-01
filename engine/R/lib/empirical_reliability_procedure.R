# Re-estimate on this run's selected sample, rather than copying coefficients
# from the saved measurement version (which can have a different sample).
reliability <- list(
  method = "standardized_alpha_and_one_factor_minres_omega",
  missingPolicy = "complete cases within each selected scale",
  constructs = lapply(metadata$constructs, function(construct) {
    ids <- unlist(construct$itemIds)
    frame <- data[, ids, drop = FALSE]
    frame <- frame[complete.cases(frame), , drop = FALSE]
    statistics <- calc_ordinal_reliability(frame, ids)
    list(
      constructId = construct$id, label = construct$label, itemCount = length(ids),
      n = nrow(frame), statistics = statistics, items = calc_item_diagnostics(frame, ids)
    )
  })
)
