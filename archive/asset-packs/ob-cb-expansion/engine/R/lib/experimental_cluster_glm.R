run_cluster_glm <- function() {
  data <- read_analysis_data()
  outcome <- spec$outcomeIds[[1]]
  factors <- unlist(lapply(spec$betweenFactors, function(factor) factor$variableId), use.names = FALSE)
  covariates <- unlist(spec$covariateIds, use.names = FALSE)
  cluster <- spec$clusterVariableId
  selected <- unique(c(outcome, factors, covariates, cluster))
  missing_columns <- setdiff(selected, names(data))
  if (length(missing_columns) > 0) stop(paste0("EXPERIMENT_COLUMN_NOT_FOUND: ", paste(missing_columns, collapse = ",")))
  frame <- data[, selected, drop = FALSE]
  for (factor_id in factors) frame[[factor_id]] <- as.factor(frame[[factor_id]])
  for (variable_id in unique(c(outcome, covariates))) frame[[variable_id]] <- suppressWarnings(as.numeric(frame[[variable_id]]))
  frame <- frame[complete.cases(frame), , drop = FALSE]
  if (nrow(frame) < 4) stop("EXPERIMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS")
  clusters <- droplevels(as.factor(frame[[cluster]]))
  cluster_count <- nlevels(clusters)
  if (cluster_count < 2) stop("GLM_CLUSTER_INSUFFICIENT_CLUSTERS")
  rhs <- unique(c(factors, covariates))
  if (length(rhs) == 0) stop("GLM_CLUSTER_DESIGN_EMPTY")
  fit <- stats::lm(stats::reformulate(rhs, response = outcome), data = frame)
  design <- stats::model.matrix(fit)
  if (qr(design)$rank < ncol(design)) stop("EXPERIMENT_DESIGN_MATRIX_RANK_DEFICIENT")
  residual <- stats::residuals(fit)
  bread <- tryCatch(solve(crossprod(design)), error = function(error) NULL)
  if (is.null(bread)) stop("GLM_CLUSTER_DESIGN_MATRIX_NOT_INVERTIBLE")
  scores <- lapply(levels(clusters), function(level) {
    rows <- which(clusters == level)
    crossprod(design[rows, , drop = FALSE], residual[rows])
  })
  meat <- Reduce("+", lapply(scores, function(score) score %*% t(score)))
  robust_vcov <- bread %*% meat %*% bread
  coefficients <- stats::coef(fit)
  standard_errors <- sqrt(pmax(diag(robust_vcov), 0))
  if (any(!is.finite(coefficients)) || any(!is.finite(standard_errors))) stop("GLM_CLUSTER_ESTIMATION_FAILED")
  df_value <- max(1, cluster_count - 1)
  coefficient_rows <- lapply(seq_along(coefficients), function(index) {
    statistic <- coefficients[[index]] / standard_errors[[index]]
    p_value <- 2 * stats::pt(abs(statistic), df = df_value, lower.tail = FALSE)
    margin <- stats::qt(as.numeric(spec$confidenceLevel), df = df_value) * standard_errors[[index]]
    list(term = names(coefficients)[[index]], estimate = as.numeric(coefficients[[index]]), standardError = as.numeric(standard_errors[[index]]), statistic = as.numeric(statistic), degreesOfFreedom = as.numeric(df_value), pValue = as.numeric(p_value), confidenceLower = as.numeric(coefficients[[index]] - margin), confidenceUpper = as.numeric(coefficients[[index]] + margin))
  })
  list(
    sampleFlow = list(original = nrow(data), included = nrow(frame), excluded = nrow(data) - nrow(frame), missingMethod = "complete cases", clusters = cluster_count),
    estimates = lapply(coefficient_rows, function(row) estimate_entry(row$term, row$term, row$estimate, row$standardError, row$statistic, row$degreesOfFreedom, row$pValue, row$confidenceLower, row$confidenceUpper, "outcome")),
    diagnostics = list(message_entry("GLM_CLUSTER_CR0", "info", "Coefficient uncertainty uses cluster-robust CR0 covariance with cluster-level t degrees of freedom.")),
    warnings = if (cluster_count < 30) list(message_entry("GLM_CLUSTER_SMALL_CLUSTER_COUNT", "warning", "少于 30 个 cluster；CR0 小样本偏差可能较大，当前不冒充 CR2。")) else list(),
    provenance = list(engine = "ResearchPath base R lm cluster robust", engineVersion = R.version.string, softwareVersions = package_versions(c("stats")), estimand = "conditional mean difference with CR0 cluster-robust uncertainty", degreesOfFreedomMethod = "cluster count minus one"),
    familyResult = list(family = family, analysisType = "glm_cluster", coefficients = coefficient_rows, clusterVariableId = cluster, clusterCount = cluster_count, standardErrorMethod = "CR0"),
    apaReports = list(sprintf("A cluster-robust linear model was fit with %s clusters.", cluster_count))
  )
}

prepare_experimental_data <- function(data) {
  within <- spec$withinFactors
  if (identical(spec$dataLayout, "wide") && length(within) > 0L) {
    if (length(within) != 1L) stop("Wide repeated-measures execution currently supports one within factor")
    factor <- within[[1]]
    levels <- unlist(factor$levels)
    columns <- unlist(factor$columns)[levels]
    subject <- spec$subjectId
    retained <- unique(c(subject, vapply(spec$betweenFactors, `[[`, character(1), "variableId"), unlist(spec$covariateIds)))
    pieces <- lapply(seq_along(levels), function(index) {
      piece <- data[, retained, drop = FALSE]
      piece[[factor$id]] <- levels[[index]]
      piece[[spec$outcomeIds[[1]]]] <- data[[columns[[index]]]]
      piece
    })
    data <- do.call(rbind, pieces)
  }
  data
}
