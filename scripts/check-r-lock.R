args <- commandArgs(trailingOnly = TRUE)
project_root <- if (length(args) >= 1) normalizePath(args[[1]], winslash = "/") else getwd()
lock_path <- file.path(project_root, "renv.lock")
library_path <- Sys.getenv("R_LIBS_USER")

if (!file.exists(lock_path)) stop("renv.lock is missing")
if (!nzchar(library_path) || !dir.exists(library_path)) stop("R_LIBS_USER is not configured")
.libPaths(unique(c(library_path, .libPaths())))
if (!requireNamespace("jsonlite", quietly = TRUE)) stop("jsonlite is required to validate renv.lock")

lock <- jsonlite::fromJSON(lock_path, simplifyVector = FALSE)

# Use all library paths that R actually sees, not just R_LIBS_USER.
# Recommended packages (Matrix, MASS, boot, etc.) live in R's base library,
# while user-installed packages are in R_LIBS_USER.
all_libs <- .libPaths()
installed <- installed.packages(lib.loc = all_libs)
failures <- character()

for (package_name in names(lock$Packages)) {
  expected <- lock$Packages[[package_name]]$Version
  if (!(package_name %in% rownames(installed))) {
    failures <- c(failures, sprintf("%s is missing (expected %s)", package_name, expected))
  } else {
    actual <- installed[package_name, "Version"]
    if (!identical(actual, expected)) {
      failures <- c(failures, sprintf("%s is %s (expected %s)", package_name, actual, expected))
    }
    # Compiled packages must actually load their namespace: version equality
    # alone cannot catch ABI mismatches (e.g. qs2.dll LoadLibrary failure when
    # a package links a dependency version outside the lock).
    needs_compilation <- lock$Packages[[package_name]]$NeedsCompilation
    if (!is.null(needs_compilation) &&
        tolower(as.character(needs_compilation)) %in% c("yes", "true", "1")) {
      loaded <- tryCatch(
        {
          loadNamespace(package_name, lib.loc = all_libs)
          TRUE
        },
        error = function(e) FALSE
      )
      if (!loaded) {
        failures <- c(
          failures,
          sprintf("%s %s is installed but its namespace fails to load (DLL/ABI problem?)", package_name, expected)
        )
      }
    }
  }
}

if (length(failures)) stop(paste(failures, collapse = "; "))
cat(sprintf("R lock check passed (%d packages, R %s).\n", length(lock$Packages), lock$R$Version))
