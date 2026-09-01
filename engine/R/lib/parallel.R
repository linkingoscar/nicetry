researchpath_parallel_workers <- function(task_count = NULL) {
  configured <- suppressWarnings(as.integer(Sys.getenv("RESEARCHPATH_PARALLEL_WORKERS", "1")))
  if (is.na(configured) || configured < 1L) configured <- 1L
  if (!is.null(task_count)) configured <- min(configured, max(1L, as.integer(task_count)))
  configured
}

researchpath_parallel_profile <- function(task_count = NULL) {
  workers <- researchpath_parallel_workers(task_count)
  available <- workers > 1L &&
    requireNamespace("future", quietly = TRUE) &&
    requireNamespace("future.apply", quietly = TRUE)
  list(
    backend = if (available) "future_multisession" else "sequential",
    workers = if (available) workers else 1L,
    rngStrategy = "deterministic per-replicate seeds"
  )
}

researchpath_ensure_future_plan <- function(workers) {
  configured <- getOption("researchpath.future.workers", 0L)
  if (!identical(as.integer(configured), as.integer(workers))) {
    future::plan(future::multisession, workers = workers)
    options(researchpath.future.workers = as.integer(workers))
  }
  invisible(NULL)
}

researchpath_parallel_grouped_lapply <- function(values, callback, workers = NULL) {
  if (length(values) == 0L) return(list())
  if (is.null(workers)) workers <- researchpath_parallel_workers(length(values))
  profile <- researchpath_parallel_profile(length(values))
  workers <- min(as.integer(workers), as.integer(profile$workers), length(values))
  if (workers <= 1L || !identical(profile$backend, "future_multisession")) {
    return(lapply(values, callback))
  }
  group_id <- cut(seq_along(values), breaks = workers, labels = FALSE)
  groups <- split(values, group_id)
  group_environment <- new.env(parent = globalenv())
  group_callback <- eval(
    quote(function(group, item_callback) lapply(group, item_callback)),
    envir = group_environment
  )
  researchpath_ensure_future_plan(workers)
  grouped_results <- future.apply::future_lapply(
    groups,
    group_callback,
    item_callback = callback,
    future.seed = NULL,
    future.globals = FALSE,
    future.scheduling = 1,
    future.stdout = FALSE
  )
  unname(do.call(c, grouped_results))
}

researchpath_use_parallel <- function(work_units, task_count) {
  profile <- researchpath_parallel_profile(task_count)
  threshold <- suppressWarnings(as.double(Sys.getenv(
    "RESEARCHPATH_PARALLEL_MIN_WORK_UNITS",
    "5000000"
  )))
  if (is.na(threshold) || threshold < 0) threshold <- 5000000
  identical(profile$backend, "future_multisession") &&
    is.finite(work_units) &&
    work_units >= threshold
}

researchpath_parallel_chunks <- function(total, workers = NULL, tasks_per_worker = 250L) {
  total <- as.integer(total)
  if (total <= 0L) return(list())
  if (is.null(workers)) workers <- researchpath_parallel_workers(total)
  chunk_size <- max(1L, as.integer(workers) * as.integer(tasks_per_worker))
  indices <- seq_len(total)
  split(indices, ceiling(indices / chunk_size))
}
