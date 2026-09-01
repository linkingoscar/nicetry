measurement_invariance <- list(available = FALSE, reason = "未选择分组变量")
if (!non_iid_context && !is.null(options$groupVariableId) && options$groupVariableId != "") {
  invariance_items <- unique(unlist(lapply(metadata$constructs, function(construct) unlist(construct$itemIds))))
  invariance_items <- intersect(invariance_items, names(data))
  invariance_data <- data[, unique(c(invariance_items, options$groupVariableId)), drop = FALSE]
  factor_syntax <- vapply(metadata$constructs, function(construct) {
    factor_name <- paste0("F_", gsub("[^A-Za-z0-9_]", "_", construct$id))
    ids <- intersect(unlist(construct$itemIds), invariance_items)
    paste0(factor_name, " =~ ", paste(ids, collapse = " + "))
  }, character(1))
  measurement_invariance <- tryCatch(
    run_measurement_invariance(
      invariance_data,
      paste(factor_syntax, collapse = "\n"),
      options$groupVariableId,
      estimator = "MLR",
      partial_release = FALSE,
      missing = "listwise"
    ),
    error = function(error) list(available = FALSE, reason = as.character(error))
  )
}
