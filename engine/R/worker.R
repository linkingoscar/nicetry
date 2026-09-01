suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(lavaan))

parallel_workers <- suppressWarnings(as.integer(Sys.getenv("RESEARCHPATH_PARALLEL_WORKERS", "1")))
if (
  !is.na(parallel_workers) &&
  parallel_workers > 1L &&
  requireNamespace("future", quietly = TRUE) &&
  requireNamespace("future.apply", quietly = TRUE)
) {
  future::plan(future::multisession, workers = parallel_workers)
  options(researchpath.future.workers = parallel_workers)
  invisible(future.apply::future_lapply(
    seq_len(parallel_workers),
    identity,
    future.seed = FALSE,
    future.stdout = FALSE
  ))
}

protocol_write <- function(value) {
  cat(toJSON(value, auto_unbox = TRUE, na = "null", null = "null"), "\n", sep = "")
  flush.console()
}

restore_search_path <- function(previous_search) {
  current <- search()
  if (length(current) <= length(previous_search)) return(invisible(NULL))
  added <- current[!current %in% previous_search]
  for (name in rev(added)) {
    try(detach(name, character.only = TRUE, unload = FALSE), silent = TRUE)
  }
  invisible(NULL)
}

execute_request <- function(request) {
  request_id <- request$requestId
  output_path <- request$outputPath
  log_path <- request$logPath
  cancel_path <- if (is.null(request$cancelPath)) NULL else request$cancelPath
  if (file.exists(output_path)) unlink(output_path)
  previous_search <- search()
  task_environment <- new.env(parent = .GlobalEnv)
  task_environment$commandArgs <- function(trailingOnly = FALSE) {
    if (isTRUE(trailingOnly)) return(c(request$inputPath, output_path))
    base::commandArgs(trailingOnly = FALSE)
  }

  previous_environment <- Sys.getenv(
    c("RESEARCHPATH_RUNTIME_MODE", "RESEARCHPATH_PARALLEL_WORKERS"),
    unset = NA_character_
  )
  previous_output_sinks <- sink.number(type = "output")
  previous_message_sink <- sink.number(type = "message")
  log_connection <- NULL
  previous_options <- options()
  previous_global_vars <- ls(.GlobalEnv, all.names = TRUE)
  restore_runtime <- function() {
    options(previous_options)
    new_vars <- setdiff(ls(.GlobalEnv, all.names = TRUE), previous_global_vars)
    if (length(new_vars) > 0L) {
      rm(list = new_vars, envir = .GlobalEnv)
    }
    if (!identical(sink.number(type = "message"), previous_message_sink)) {
      try(sink(type = "message"), silent = TRUE)
    }
    while (sink.number(type = "output") > previous_output_sinks) {
      try(sink(type = "output"), silent = TRUE)
    }
    if (!is.null(log_connection) && isOpen(log_connection)) {
      try(close(log_connection), silent = TRUE)
    }
    for (name in names(previous_environment)) {
      value <- previous_environment[[name]]
      if (is.na(value)) {
        Sys.unsetenv(name)
      } else {
        do.call(Sys.setenv, setNames(list(value), name))
      }
    }
    restore_search_path(previous_search)
  }
  on.exit(restore_runtime(), add = TRUE)
  Sys.setenv(
    RESEARCHPATH_RUNTIME_MODE = "resident_pool",
    RESEARCHPATH_PARALLEL_WORKERS = as.character(request$parallelWorkers)
  )
  log_connection <- file(log_path, open = "wt", encoding = "UTF-8")
  sink(log_connection, type = "output")
  sink(log_connection, type = "message")
  error_message <- NULL
  tryCatch(
    sys.source(request$scriptPath, envir = task_environment, keep.source = FALSE),
    error = function(error) {
      error_message <<- conditionMessage(error)
    }
  )
  sink(type = "message")
  sink(type = "output")
  close(log_connection)
  log_connection <- NULL
  previous_message_sink <- sink.number(type = "message")
  previous_output_sinks <- sink.number(type = "output")
  for (name in names(previous_environment)) {
    value <- previous_environment[[name]]
    if (is.na(value)) {
      Sys.unsetenv(name)
    } else {
      do.call(Sys.setenv, setNames(list(value), name))
    }
  }
  previous_environment <- character()
  rm(task_environment)
  invisible(gc(verbose = FALSE))

  if (!is.null(error_message)) {
    if (file.exists(output_path)) unlink(output_path)
    is_cancelled <- (!is.null(cancel_path) && file.exists(cancel_path)) || error_message == "ANALYSIS_CANCELLED"
    return(list(requestId = request_id, ok = FALSE, error = error_message, cancelled = is_cancelled))
  }
  list(requestId = request_id, ok = file.exists(output_path), error = NULL)
}

protocol_write(list(type = "ready", pid = Sys.getpid()))
input_connection <- file("stdin", open = "r", encoding = "UTF-8")
repeat {
  line <- readLines(input_connection, n = 1L, warn = FALSE)
  if (length(line) == 0L) break
  request <- tryCatch(fromJSON(line, simplifyVector = FALSE), error = function(error) NULL)
  if (is.null(request)) {
    protocol_write(list(requestId = NULL, ok = FALSE, error = "invalid worker request"))
    next
  }
  if (identical(request$type, "shutdown")) break
  response <- tryCatch(
    execute_request(request),
    error = function(error) list(
      requestId = request$requestId,
      ok = FALSE,
      error = conditionMessage(error)
    )
  )
  protocol_write(response)
}

if (requireNamespace("future", quietly = TRUE)) future::plan(future::sequential)
close(input_connection)
