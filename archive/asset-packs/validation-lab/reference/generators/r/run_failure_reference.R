args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_failure_reference.R <case-dir> <output.json>")
suppressPackageStartupMessages(library(jsonlite))

case_dir <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
manifest <- yaml::read_yaml(file.path(case_dir, "manifest.yaml"))
spec <- jsonlite::fromJSON(file.path(case_dir, manifest$specPath), simplifyVector = FALSE)
data <- utils::read.csv(file.path(case_dir, "data", "input.csv"), check.names = FALSE,
  stringsAsFactors = FALSE)
capability <- manifest$identity$capabilityId

failure <- function(reason_code, message) {
  list(status = "failed", failure = list(reasonCode = reason_code, message = message))
}

result <- switch(capability,
  "multilevel.icc.two_level.v1" = {
    cluster <- spec$clusterVariable
    if (!cluster %in% names(data) || length(unique(stats::na.omit(data[[cluster]]))) < 2L) {
      failure("MISSING_CLUSTER_VARIABLE", "ICC calculation requires at least 2 distinct clusters")
    } else stop("expected ICC cluster failure did not trigger")
  },
  "multilevel.lmm.within_between.v1" = {
    cluster <- spec$data$clusterVar
    if (!cluster %in% names(data) || length(unique(stats::na.omit(data[[cluster]]))) < 2L) {
      failure("MISSING_CLUSTER_VARIABLE",
        "Fewer than minimum required clusters for multilevel model estimation")
    } else stop("expected within-between cluster failure did not trigger")
  },
  "experiment.between.factorial.gaussian.v1" = {
    factors <- vapply(spec$betweenFactors, `[[`, character(1), "variableId")
    observed <- nrow(unique(data[, factors, drop = FALSE]))
    possible <- prod(vapply(factors, function(name) length(unique(data[[name]])), integer(1)))
    if (observed < possible) {
      failure("RANK_DEFICIENT_DESIGN",
        "Factorial design contains empty cells or rank deficient matrix")
    } else stop("expected rank-deficient factorial failure did not trigger")
  },
  "experiment.emmeans.planned_contrast.v1" = {
    factor_name <- spec$betweenFactors[[1]]$variableId
    if (length(unique(stats::na.omit(data[[factor_name]]))) < 2L) {
      failure("INVALID_CONTRAST_WEIGHTS",
        "Factor has fewer than 2 levels; cannot compute contrasts")
    } else stop("expected contrast failure did not trigger")
  },
  "experiment.repeated.one_within.v1" = {
    subject <- spec$subjectId
    within <- spec$withinFactors[[1]]$id
    expected_cells <- length(unique(stats::na.omit(data[[within]])))
    counts <- tapply(data[[within]], data[[subject]], function(values) length(unique(values)))
    if (length(counts) == 0L || any(counts != expected_cells)) {
      failure("MISSING_REPEATED_MEASUREMENT",
        "Repeated measures design contains missing cells or incomplete subject observations")
    } else stop("expected repeated-measurement failure did not trigger")
  },
  "imputation.mice.chain_diagnostics.v1" = {
    variables <- vapply(spec$variables, `[[`, character(1), "variableId")
    invalid <- variables[vapply(variables, function(name) {
      values <- data[[name]]
      converted <- suppressWarnings(as.numeric(values))
      any(!is.na(values) & is.na(converted))
    }, logical(1))]
    if (length(invalid)) {
      failure("UNSUPPORTED_VARIABLE_TYPE",
        paste0("Column ", invalid[[1]], " contains non-numeric text values unsupported by PMM"))
    } else stop("expected unsupported-variable failure did not trigger")
  },
  "multilevel.lmm.two_level.gaussian.random_slope.v1" = {
    cluster <- spec$clusterVariableId
    if (!cluster %in% names(data) || length(unique(stats::na.omit(data[[cluster]]))) < 2L) {
      failure("MISSING_CLUSTER_VARIABLE",
        "Fewer than minimum required clusters for multilevel model estimation")
    } else stop("expected LMM cluster failure did not trigger")
  },
  "multilevel.se.cluster_robust.v1" = {
    cluster <- spec$data$clusterVar
    if (!cluster %in% names(data) || length(unique(stats::na.omit(data[[cluster]]))) < 2L) {
      failure("MISSING_CLUSTER_VARIABLE",
        "Cluster-robust SE estimation requires at least 2 distinct clusters")
    } else stop("expected CR2 cluster failure did not trigger")
  },
  "multilevel.mediation.two_level.v1" = {
    cluster <- spec$data$clusterVar
    if (!cluster %in% names(data) || length(unique(stats::na.omit(data[[cluster]]))) < 2L) {
      failure("MISSING_CLUSTER_VARIABLE",
        "Two-level mediation requires at least 2 distinct clusters")
    } else stop("expected mediation cluster failure did not trigger")
  },
  "longitudinal.esm.diary_ar1.v1" = {
    person <- spec$data$personVar
    if (!person %in% names(data) || length(unique(stats::na.omit(data[[person]]))) < 2L) {
      failure("MISSING_PERSON_VARIABLE",
        "ESM diary AR(1) model requires at least 2 distinct subjects")
    } else stop("expected ESM person failure did not trigger")
  },
  "longitudinal.ri_clpm.four_wave.v1" = {
    variables <- unlist(lapply(spec$waves, function(wave) unlist(wave$variables)))
    if (length(spec$waves) != 4L || any(!variables %in% names(data))) {
      failure("INSUFFICIENT_WAVES",
        "Four-wave RI-CLPM requires exactly 4 distinct waves of measurements")
    } else stop("expected RI-CLPM wave failure did not trigger")
  },
  "robustness.specification_curve.matrix.v1" = {
    predictor <- spec$data$x
    if (!predictor %in% names(data)) {
      failure("MISSING_PREDICTOR_VARIABLE",
        paste0("Predictor variable '", predictor, "' is missing from input dataset"))
    } else stop("expected specification-curve predictor failure did not trigger")
  },
  "measurement.cfa.continuous.mlr.v1" = {
    minimum <- min(vapply(spec$constructs, function(item) length(unlist(item$itemIds)), integer(1)))
    if (minimum < 3L) {
      failure("UNDERIDENTIFIED_MODEL",
        "CFA model is underidentified; requires at least 3 indicators per factor")
    } else stop("expected CFA identification failure did not trigger")
  },
  "measurement.cfa.ordinal.wlsmv.v1" = {
    items <- unlist(spec$itemIds)
    counts <- vapply(items, function(item) length(unique(stats::na.omit(data[[item]]))), integer(1))
    if (any(counts < 2L)) {
      item <- items[which(counts < 2L)[[1]]]
      failure("ZERO_VARIANCE_INDICATOR",
        paste0("Item '", item, "' has zero variance (only 1 category observed)"))
    } else stop("expected ordinal CFA variance failure did not trigger")
  },
  "measurement.invariance.multi_group.v1" = {
    group <- spec$groupVariableId
    if (!group %in% names(data) || length(unique(stats::na.omit(data[[group]]))) < 2L) {
      failure("MISSING_GROUP_VARIABLE",
        paste0("Group variable '", group, "' contains fewer than 2 distinct groups"))
    } else stop("expected invariance group failure did not trigger")
  },
  "measurement.efa.continuous.minres.v1" = {
    items <- unlist(spec$itemIds)
    factors <- as.integer(spec$factorCount)
    if (length(items) <= factors) {
      failure("INSUFFICIENT_ITEMS",
        paste0("EFA model requires more items than factors (", length(items), " items for ",
          factors, " factors is underidentified)"))
    } else stop("expected EFA identification failure did not trigger")
  },
  "measurement.bifactor.continuous.v1" = {
    items <- unlist(spec$itemIds)
    counts <- vapply(spec$constructs, function(item) length(unlist(item$itemIds)), integer(1))
    if (length(items) < 3L || any(counts < 2L)) {
      failure("UNDERIDENTIFIED_SPECIFIC_FACTOR",
        "Bifactor model requires at least 2 items per specific factor and 3 total specific items")
    } else stop("expected bifactor identification failure did not trigger")
  },
  stop(paste0("unsupported failure reference capability: ", capability))
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE, null = "null")
