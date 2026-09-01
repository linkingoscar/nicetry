run_aggregation <- function() {
  data <- read_analysis_data()
  item_ids <- unique(unlist(spec$scaleItemIds, use.names = FALSE))
  missing_columns <- setdiff(c(item_ids, spec$clusterVariableId), names(data))
  if (length(missing_columns) > 0) stop(paste0("AGGREGATION_COLUMN_NOT_FOUND: ", paste(missing_columns, collapse = ",")))
  item_frame <- data[, item_ids, drop = FALSE]
  for (item_id in item_ids) item_frame[[item_id]] <- suppressWarnings(as.numeric(item_frame[[item_id]]))
  score <- if (identical(spec$aggregationMethod, "sum")) rowSums(item_frame, na.rm = FALSE) else rowMeans(item_frame, na.rm = FALSE)
  analysis_data <- data.frame(.rp_aggregation_score = score, .rp_cluster = data[[spec$clusterVariableId]])
  evidence <- calc_multilevel_aggregation(
    analysis_data,
    ".rp_aggregation_score",
    ".rp_cluster",
    as.numeric(spec$scaleMin),
    as.numeric(spec$scaleMax),
    length(item_ids),
    spec$aggregationMethod
  )
  estimates <- list(
    estimate_entry("icc1", "ICC(1)", evidence$icc1, scale = "reliability"),
    estimate_entry("icc2", "ICC(2)", evidence$icc2, scale = "reliability"),
    estimate_entry("mean_rwg", "Mean rwg", evidence$meanRwg, scale = "reliability")
  )
  included <- sum(complete.cases(analysis_data))
  list(
    sampleFlow = list(original = nrow(data), included = included, excluded = nrow(data) - included, missingMethod = "complete_cases", clusters = evidence$numClusters),
    estimates = estimates,
    diagnostics = list(message_entry("AGGREGATION_EVIDENCE_COMPLETED", "info", evidence$diagnosticMessage)),
    warnings = list(),
    provenance = list(engine = "ResearchPath R aggregation evidence", engineVersion = "0.1.0", softwareVersions = package_versions(c("stats")), estimand = "cluster-level aggregation evidence", degreesOfFreedomMethod = "ANOVA mean squares"),
    familyResult = list(family = family, analysisType = "aggregation", aggregation = evidence)
  )
}
