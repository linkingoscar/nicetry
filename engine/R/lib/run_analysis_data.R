raw <- read.csv(payload$dataPath, check.names = FALSE, na.strings = c("", "NA"), fileEncoding = "UTF-8")
required_columns <- unique(vapply(spec$nodes, function(node) node$variableId, character(1)))
missing_columns <- setdiff(required_columns, names(raw))
if (length(missing_columns) > 0) stop(sprintf("Missing required columns: %s", paste(missing_columns, collapse = ", ")))

analysis_data <- data.frame(row.names = seq_len(nrow(raw)))
binary_level_mappings <- list()
for (node in spec$nodes) {
  source_values <- raw[[node$variableId]]
  encoding <- node$encoding
  encoding_method <- if (!is.null(encoding$method)) encoding$method else if (identical(node$dataType, "binary")) "binary_indicator" else if (identical(node$dataType, "nominal")) "treatment" else if (identical(node$dataType, "ordinal")) "ordinal_score" else "as_is"
  configured_levels <- if (is.null(encoding$levels)) character(0) else as.character(unlist(encoding$levels))
  if (identical(encoding_method, "binary_indicator")) {
    text_values <- as.character(source_values)
    valid <- !is.na(source_values) & text_values != ""
    levels_found <- if (length(configured_levels) > 0) configured_levels else unique(text_values[valid])
    numeric_levels <- suppressWarnings(as.numeric(levels_found))
    if (length(levels_found) != 2) stop(sprintf("Binary variable %s must contain exactly two non-missing levels", node$label))
    if (!is.null(encoding$referenceLevel) && as.character(encoding$referenceLevel) %in% levels_found) {
      reference <- as.character(encoding$referenceLevel)
      ordered_levels <- c(reference, setdiff(levels_found, reference))
    } else if (all(is.finite(numeric_levels))) {
      ordered_levels <- levels_found[order(numeric_levels)]
    } else {
      ordered_levels <- sort(levels_found)
    }
    encoded <- rep(NA_real_, length(source_values))
    encoded[valid] <- match(text_values[valid], ordered_levels) - 1
    analysis_data[[node$id]] <- encoded
    binary_level_mappings[[node$id]] <- list(reference = ordered_levels[[1]], event = ordered_levels[[2]])
  } else if (identical(encoding_method, "treatment")) {
    text_values <- as.character(source_values)
    valid_levels <- if (length(configured_levels) > 0) configured_levels else sort(unique(text_values[!is.na(source_values) & text_values != ""]))
    if (length(valid_levels) < 2) stop(sprintf("Categorical variable %s must contain at least two levels", node$label))
    reference <- if (!is.null(encoding$referenceLevel) && as.character(encoding$referenceLevel) %in% valid_levels) as.character(encoding$referenceLevel) else valid_levels[[1]]
    ordered_levels <- c(reference, setdiff(valid_levels, reference))
    analysis_data[[node$id]] <- factor(text_values, levels = ordered_levels)
  } else if (identical(encoding_method, "ordinal_score") && length(configured_levels) > 0) {
    text_values <- as.character(source_values)
    encoded <- match(text_values, configured_levels)
    encoded[is.na(source_values) | text_values == ""] <- NA_integer_
    if (any(!is.na(source_values) & text_values != "" & is.na(encoded))) stop(sprintf("Ordinal variable %s contains an undeclared level", node$label))
    analysis_data[[node$id]] <- as.numeric(encoded)
  } else {
    numeric_values <- suppressWarnings(as.numeric(source_values))
    if (identical(encoding_method, "mean_center")) {
      numeric_values <- numeric_values - mean(numeric_values, na.rm = TRUE)
    } else if (identical(encoding_method, "standardize")) {
      numeric_values <- as.numeric(scale(numeric_values))
    }
    analysis_data[[node$id]] <- numeric_values
  }
}
