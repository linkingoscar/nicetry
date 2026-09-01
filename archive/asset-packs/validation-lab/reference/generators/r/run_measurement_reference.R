args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("usage: run_measurement_reference.R <case-dir> <output.json>")
suppressPackageStartupMessages(library(jsonlite))

case_dir <- normalizePath(args[[1]], winslash = "/", mustWork = TRUE)
manifest <- yaml::read_yaml(file.path(case_dir, "manifest.yaml"))
spec <- jsonlite::fromJSON(file.path(case_dir, manifest$specPath), simplifyVector = FALSE)
data <- utils::read.csv(file.path(case_dir, "data", "input.csv"), check.names = FALSE,
  stringsAsFactors = FALSE)
capability <- manifest$identity$capabilityId
items <- unlist(spec$itemIds, use.names = FALSE)
constructs <- spec$constructs
syntax <- paste(vapply(constructs, function(construct) {
  paste0("F_", construct$id, " =~ ", paste(unlist(construct$itemIds), collapse = " + "))
}, character(1)), collapse = "\n")

measure <- function(values, primary, fallback = NULL) {
  value <- unname(values[primary])
  if ((length(value) == 0L || !is.finite(value)) && !is.null(fallback)) value <- unname(values[fallback])
  as.numeric(value)
}

# Pattern-loadings have arbitrary column labels and signs.  Canonicalize them
# from the construct-to-item mapping carried by the case spec, and apply the
# exact same signed permutation to Phi.  This makes an oblique EFA comparison
# about the model, rather than an optimizer's arbitrary factor orientation.
canonicalize_efa <- function(loadings, phi, constructs, items) {
  factor_count <- ncol(loadings)
  if (length(constructs) != factor_count) return(list(loadings = loadings, phi = phi))
  source_for_target <- vapply(seq_len(factor_count), function(target) {
    target_items <- unlist(constructs[[target]]$itemIds, use.names = FALSE)
    rows <- match(target_items, items)
    rows <- rows[!is.na(rows)]
    if (length(rows) == 0L) return(target)
    scores <- colMeans(abs(loadings[rows, , drop = FALSE]))
    as.integer(which.max(scores))
  }, integer(1))
  if (length(unique(source_for_target)) != factor_count) return(list(loadings = loadings, phi = phi))
  transform <- diag(factor_count)[, source_for_target, drop = FALSE]
  for (target in seq_len(factor_count)) {
    target_items <- unlist(constructs[[target]]$itemIds, use.names = FALSE)
    rows <- match(target_items, items)
    rows <- rows[!is.na(rows)]
    if (length(rows) > 0L && mean((loadings %*% transform)[rows, target]) < 0) {
      transform[, target] <- -transform[, target]
    }
  }
  list(loadings = loadings %*% transform, phi = t(transform) %*% phi %*% transform)
}

result <- switch(capability,
  "measurement.cfa.continuous.mlr.v1" =,
  "measurement.cfa.ordinal.wlsmv.v1" = {
    ordinal <- identical(spec$itemScale, "ordinal")
    fit <- lavaan::cfa(syntax, data = data[, items, drop = FALSE], estimator = spec$estimator,
      ordered = if (ordinal) items else NULL)
    if (!isTRUE(lavaan::lavInspect(fit, "converged"))) stop("reference CFA did not converge")
    values <- lavaan::fitMeasures(fit)
    parameters <- lavaan::parameterEstimates(fit)
    loadings <- parameters[parameters$op == "=~", , drop = FALSE]
    list(
      estimator = spec$estimator,
      fit = list(
        cfi_robust = measure(values, "cfi.robust", "cfi.scaled"),
        tli_robust = measure(values, "tli.robust", "tli.scaled"),
        rmsea_robust = measure(values, "rmsea.robust", "rmsea.scaled"),
        srmr = measure(values, "srmr"),
        chisq_scaled = measure(values, "chisq.scaled", "chisq")
      ),
      loadings = lapply(seq_len(nrow(loadings)), function(index) list(
        lhs = loadings$lhs[[index]], rhs = loadings$rhs[[index]],
        est = as.numeric(loadings$est[[index]]), se = as.numeric(loadings$se[[index]])
      )),
      diagnostics = list(converged = TRUE)
    )
  },
  "measurement.invariance.multi_group.v1" = {
    frame <- data[, c(items, spec$groupVariableId), drop = FALSE]
    frame[[spec$groupVariableId]] <- factor(frame[[spec$groupVariableId]])
    fits <- list(
      configural = lavaan::cfa(syntax, data = frame, group = spec$groupVariableId),
      metric = lavaan::cfa(syntax, data = frame, group = spec$groupVariableId, group.equal = "loadings"),
      scalar = lavaan::cfa(syntax, data = frame, group = spec$groupVariableId,
        group.equal = c("loadings", "intercepts"))
    )
    if (!all(vapply(fits, function(fit) isTRUE(lavaan::lavInspect(fit, "converged")), logical(1)))) {
      stop("reference invariance model did not converge")
    }
    models <- lapply(fits, function(fit) {
      values <- lavaan::fitMeasures(fit)
      list(cfi = measure(values, "cfi"), rmsea = measure(values, "rmsea"),
        chisq = measure(values, "chisq"), df = as.integer(measure(values, "df")))
    })
    lrt <- lavaan::lavTestLRT(fits$configural, fits$metric)
    p_value <- as.numeric(lrt$`Pr(>Chisq)`[[2]])
    list(models = models, difference_test = list(
      chisq_diff = as.numeric(lrt$`Chisq diff`[[2]]),
      df_diff = as.integer(lrt$`Df diff`[[2]]), p_value = p_value,
      invariant = abs(models$metric$cfi - models$configural$cfi) <= 0.01
    ), diagnostics = list(converged = TRUE))
  },
  "measurement.efa.continuous.minres.v1" = {
    vars <- if (!is.null(spec$itemIds)) unlist(spec$itemIds) else if (!is.null(spec$variables)) unlist(spec$variables) else items
    factors <- if (!is.null(spec$factorCount)) as.integer(spec$factorCount) else if (!is.null(spec$nFactors)) as.integer(spec$nFactors) else 2L
    rotation <- if (!is.null(spec$rotation)) spec$rotation else "promax"
    fit <- psych::fa(data[, vars, drop = FALSE], nfactors = factors, fm = "minres", rotate = rotation)
    loadings <- unclass(fit$loadings)
    phi <- if (is.null(fit$Phi)) diag(ncol(loadings)) else unclass(fit$Phi)
    canonical <- canonicalize_efa(loadings, phi, constructs, vars)
    loadings <- canonical$loadings
    phi <- canonical$phi
    comms <- as.numeric(diag(loadings %*% phi %*% t(loadings)))
    list(
      loadings = lapply(seq_len(nrow(loadings)), function(index) {
        row <- list(variable = rownames(loadings)[[index]])
        for (col in seq_len(ncol(loadings))) row[[paste0("F", col)]] <- as.numeric(loadings[index, col])
        row
      }),
      communalities = lapply(seq_along(vars), function(index) list(variable = vars[[index]], est = comms[[index]])),
      factor_correlations = list(phi = as.numeric(phi[1, 2])),
      diagnostics = list(converged = if (is.null(fit$converged)) TRUE else isTRUE(fit$converged))
    )
  },
  "measurement.esem.target_rotation.v1" = {
    fit <- tryCatch(psych::fa(data[, items, drop = FALSE], nfactors = as.integer(spec$factorCount),
      rotate = "targetQ"), error = function(error) psych::fa(data[, items, drop = FALSE],
      nfactors = as.integer(spec$factorCount), rotate = "promax"))
    loadings <- unclass(fit$loadings)
    phi <- if (is.null(fit$Phi)) diag(ncol(loadings)) else unclass(fit$Phi)
    list(rotated_loadings = lapply(seq_len(nrow(loadings)), function(index) {
      row <- list(item = rownames(loadings)[[index]])
      for (column in seq_len(ncol(loadings))) row[[paste0("F", column)]] <- as.numeric(loadings[index, column])
      row
    }), factor_correlations = list(phi_F1_F2 = as.numeric(phi[1, 2])),
    diagnostics = list(converged = TRUE))
  },
  "measurement.bifactor.continuous.v1" = {
    specific_names <- paste0("S_", vapply(constructs, function(construct) construct$id, character(1)))
    bifactor_syntax <- c(paste0("G_factor =~ ", paste(items, collapse = " + ")),
      vapply(seq_along(constructs), function(index) paste0(specific_names[[index]], " =~ ",
        paste(unlist(constructs[[index]]$itemIds), collapse = " + ")), character(1)))
    factor_names <- c("G_factor", specific_names)
    for (left in seq_len(length(factor_names) - 1L)) for (right in (left + 1L):length(factor_names)) {
      bifactor_syntax <- c(bifactor_syntax, paste0(factor_names[[left]], " ~~ 0*", factor_names[[right]]))
    }
    fit <- lavaan::cfa(paste(bifactor_syntax, collapse = "\n"), data = data[, items, drop = FALSE],
      estimator = "ML", bounds = "pos.var")
    solution <- lavaan::standardizedSolution(fit)
    loading_rows <- solution[solution$op == "=~", , drop = FALSE]
    residual_rows <- solution[solution$op == "~~" & solution$lhs == solution$rhs & solution$lhs %in% items, ]
    general <- vapply(items, function(item) loading_rows$est.std[loading_rows$lhs == "G_factor" & loading_rows$rhs == item][[1]], numeric(1))
    specific <- vapply(items, function(item) loading_rows$est.std[loading_rows$lhs != "G_factor" & loading_rows$rhs == item][[1]], numeric(1))
    residuals <- vapply(items, function(item) residual_rows$est.std[residual_rows$lhs == item][[1]], numeric(1))
    g_sq <- sum(general^2); s_sq <- sum(specific^2)
    omega_h <- sum(general)^2 / (sum(general)^2 + sum(specific^2) + sum(residuals))
    within_pairs <- sum(vapply(constructs, function(construct) {
      count <- length(unlist(construct$itemIds)); count * (count - 1) / 2
    }, numeric(1)))
    total_pairs <- length(items) * (length(items) - 1) / 2
    list(
      general_loadings = lapply(seq_along(items), function(index) list(item = items[[index]], est = general[[index]])),
      specific_loadings = lapply(seq_along(items), function(index) list(item = items[[index]], est = specific[[index]])),
      indices = list(omega_h = omega_h, ecv = g_sq / (g_sq + s_sq), puc = (total_pairs - within_pairs) / total_pairs),
      diagnostics = list(converged = isTRUE(lavaan::lavInspect(fit, "converged")))
    )
  },
  "measurement.cmb.ulmc.v1" = {
    frame <- data[, items, drop = FALSE]
    baseline <- lavaan::cfa(syntax, data = frame, estimator = "ML")
    method_line <- paste0("ULMC_Method =~ ", paste(paste0("m*", items), collapse = " + "))
    orthogonal <- vapply(constructs, function(construct) paste0("ULMC_Method ~~ 0*F_", construct$id), character(1))
    ulmc <- lavaan::cfa(paste(c(syntax, method_line, orthogonal), collapse = "\n"), data = frame,
      estimator = "ML", bounds = "pos.var")
    base_values <- lavaan::fitMeasures(baseline); ulmc_values <- lavaan::fitMeasures(ulmc)
    lrt <- lavaan::lavTestLRT(baseline, ulmc)
    delta_cfi <- measure(ulmc_values, "cfi") - measure(base_values, "cfi")
    p_value <- as.numeric(lrt$`Pr(>Chisq)`[[2]])
    list(fit_comparison = list(
      baseline_cfi = measure(base_values, "cfi"), ulmc_cfi = measure(ulmc_values, "cfi"),
      delta_cfi = delta_cfi, delta_chisq = as.numeric(lrt$`Chisq diff`[[2]]), p_value = p_value
    ), cmb_present = isTRUE(p_value < 0.05 && delta_cfi > 0.01),
    diagnostics = list(converged = isTRUE(lavaan::lavInspect(ulmc, "converged"))))
  },
  "measurement.irt.dif.v1" = {
    frame <- data[, items, drop = FALSE]
    fit <- mirt::mirt(frame, 1L, itemtype = "2PL", verbose = FALSE,
      technical = list(NCYCLES = 1000L))
    parameters <- mirt::coef(fit, IRTpars = TRUE, simplify = TRUE)$items
    theta <- as.numeric(mirt::fscores(fit, method = "EAP")[, 1])
    groups <- factor(data[[spec$groupVariableId]])
    dif <- lapply(items, function(item) {
      reduced <- stats::glm(frame[[item]] ~ theta, family = stats::binomial())
      full <- stats::glm(frame[[item]] ~ theta + groups, family = stats::binomial())
      comparison <- stats::anova(reduced, full, test = "LRT")
      p_value <- as.numeric(comparison$`Pr(>Chi)`[[2]])
      list(item = item, uniform_chisq = as.numeric(comparison$Deviance[[2]]),
        p_value = p_value, has_dif = p_value < 0.05)
    })
    list(item_parameters = lapply(items, function(item) list(item = item,
      a = as.numeric(parameters[item, "a"]), b = as.numeric(parameters[item, "b"]))),
      dif_tests = dif, diagnostics = list(converged = isTRUE(fit@OptimInfo$converged)))
  },
  stop(paste0("unsupported measurement reference capability: ", capability))
)

jsonlite::write_json(result, args[[2]], auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null")
