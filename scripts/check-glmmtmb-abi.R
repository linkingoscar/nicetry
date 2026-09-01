#!/usr/bin/env Rscript

mismatch <- FALSE
mismatch_message <- NULL

invisible(withCallingHandlers(
  loadNamespace("glmmTMB"),
  warning = function(condition) {
    message <- conditionMessage(condition)
    if (grepl(
      "glmmTMB was built with TMB package version",
      message,
      fixed = TRUE
    )) {
      mismatch <<- TRUE
      mismatch_message <<- message
    }
    invokeRestart("muffleWarning")
  }
))

if (mismatch) {
  message("glmmTMB/TMB ABI mismatch: ", mismatch_message)
  quit(status = 1L)
}

cat(
  sprintf(
    "glmmTMB/TMB ABI check passed (glmmTMB %s, TMB %s).\n",
    as.character(packageVersion("glmmTMB")),
    as.character(packageVersion("TMB"))
  )
)
