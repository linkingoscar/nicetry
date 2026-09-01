args <- commandArgs(trailingOnly = TRUE)
project_root <- if (length(args) >= 1L) args[[1]] else getwd()
project_root <- normalizePath(project_root, winslash = "/", mustWork = TRUE)
Sys.setenv(RESEARCHPATH_PROJECT_ROOT = project_root)
test_filter <- if (length(args) >= 2L && nzchar(args[[2]])) args[[2]] else NULL
test_invert <- length(args) >= 3L && identical(args[[3]], "invert")

suppressPackageStartupMessages(library(testthat))

package_version_or_missing <- function(package) {
  if (!requireNamespace(package, quietly = TRUE)) return("missing")
  as.character(packageVersion(package))
}

cat(
  paste0(
    "R numeric test environment: ",
    R.version.string,
    "; testthat=", package_version_or_missing("testthat"),
    "; lavaan=", package_version_or_missing("lavaan"),
    "; psych=", package_version_or_missing("psych"),
    "; lme4=", package_version_or_missing("lme4"),
    if (is.null(test_filter)) "" else paste0("; testFilter=", test_filter,
      if (test_invert) " (invert)" else ""),
    "\n"
  )
)

test_dir(
  file.path(project_root, "engine", "R", "tests", "testthat"),
  filter = test_filter,
  invert = test_invert,
  reporter = SummaryReporter$new(),
  stop_on_failure = TRUE,
  stop_on_warning = FALSE
)
