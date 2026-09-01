finite_number <- function(value) {
  if (is.null(value) || length(value) == 0) return(NA_real_)
  # Ordinary NA stays a normal missing value. NaN/Inf/-Inf are preserved so
  # researchpath_write_result can convert them to null and record their exact
  # JSON Pointer path in provenance.nonFiniteValues; collapsing them here would
  # erase the originalKind traceability.
  as.numeric(value)
}

finite <- finite_number

researchpath_validate_confidence_level <- function(value, label = "confidenceLevel") {
  level <- suppressWarnings(as.numeric(value))
  if (length(level) != 1L || !is.finite(level) || level <= 0.5 || level >= 1) {
    stop(sprintf("%s 必须位于 (0.5, 1.0) 区间", label), call. = FALSE)
  }
  level
}

message_entry <- function(code, severity, message) {
  list(code = code, severity = severity, message = message)
}

estimate_entry <- function(id, label, estimate, se = NULL, statistic = NULL, df = NULL, p = NULL, lower = NULL, upper = NULL, scale = "raw") {
  list(
    id = id, label = label, estimate = as.numeric(estimate),
    standardError = finite(se), statistic = finite(statistic),
    degreesOfFreedom = finite(df), pValue = finite(p),
    confidenceLower = finite(lower), confidenceUpper = finite(upper), scale = scale
  )
}

package_versions <- function(packages) {
  values <- vapply(packages, function(package) as.character(packageVersion(package)), character(1))
  as.list(values)
}

write_progress <- function(stage, progress, completed = 0L, total = 0L) {
  if (is.null(progress_path)) return(invisible(NULL))
  temporary <- paste0(progress_path, ".tmp")
  write_json(list(stage = stage, progress = progress, completedReplicates = completed, totalReplicates = total), temporary, auto_unbox = TRUE)
  file.rename(temporary, progress_path)
}

# 将结果写入临时文件、校验可解析后原子替换最终路径，
# 避免进程崩溃时在输出位置留下截断/损坏的 JSON。
safe_write_json <- function(result, path, ...) {
  temporary <- paste0(path, ".tmp.", Sys.getpid())
  on.exit(unlink(temporary), add = TRUE)
  write_json(result, path = temporary, ...)
  if (!file.exists(temporary)) {
    stop("failed to write result JSON")
  }
  parsed <- tryCatch(
    {
      fromJSON(temporary)
      TRUE
    },
    error = function(error) FALSE
  )
  if (!parsed) stop("result JSON failed serialization check")
  if (file.exists(path) && !file.remove(path)) {
    stop("failed to replace previous result JSON")
  }
  if (!file.rename(temporary, path)) {
    if (!file.copy(temporary, path, overwrite = TRUE)) {
      stop("failed to move result JSON into place")
    }
    unlink(temporary)
  }
  invisible(NULL)
}

check_cancel <- function() {
  if (!is.null(cancel_path) && file.exists(cancel_path)) stop("ANALYSIS_CANCELLED")
}
