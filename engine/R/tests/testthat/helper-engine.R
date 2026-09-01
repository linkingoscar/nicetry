project_root <- Sys.getenv("RESEARCHPATH_PROJECT_ROOT")
if (!nzchar(project_root)) stop("RESEARCHPATH_PROJECT_ROOT is required")

source_engine <- function(relative_path) {
  source(
    file.path(project_root, "engine", "R", relative_path),
    local = globalenv(),
    encoding = "UTF-8"
  )
}
