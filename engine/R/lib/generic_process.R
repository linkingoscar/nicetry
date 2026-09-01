# 独立加载（测试/复用）时引导 seed 工具；入口脚本已先行 source。
if (!exists("researchpath_seed", mode = "function", inherits = TRUE)) {
  if (file.exists(file.path("engine", "R", "lib", "seed_utils.R"))) {
    source(file.path("engine", "R", "lib", "seed_utils.R"))
  }
}

rp_poly_key <- function(power_w, power_z) paste0(power_w, ",", power_z)

rp_poly_add_term <- function(polynomial, power_w, power_z, value) {
  key <- rp_poly_key(power_w, power_z)
  current <- if (key %in% names(polynomial)) polynomial[[key]] else 0
  polynomial[[key]] <- current + value
  polynomial
}

rp_poly_add <- function(left, right) {
  result <- left
  for (key in names(right)) {
    powers <- as.integer(strsplit(key, ",", fixed = TRUE)[[1]])
    result <- rp_poly_add_term(result, powers[[1]], powers[[2]], right[[key]])
  }
  result
}

rp_poly_multiply <- function(left, right) {
  result <- list()
  for (left_key in names(left)) {
    left_powers <- as.integer(strsplit(left_key, ",", fixed = TRUE)[[1]])
    for (right_key in names(right)) {
      right_powers <- as.integer(strsplit(right_key, ",", fixed = TRUE)[[1]])
      result <- rp_poly_add_term(
        result,
        left_powers[[1]] + right_powers[[1]],
        left_powers[[2]] + right_powers[[2]],
        left[[left_key]] * right[[right_key]]
      )
    }
  }
  result
}

rp_poly_evaluate <- function(polynomial, w_value = 0, z_value = 0) {
  sum(vapply(names(polynomial), function(key) {
    powers <- as.integer(strsplit(key, ",", fixed = TRUE)[[1]])
    polynomial[[key]] * w_value^powers[[1]] * z_value^powers[[2]]
  }, numeric(1)))
}

rp_indirect_paths <- function(edges, x_id, y_id) {
  adjacency <- split(edges, vapply(edges, function(edge) edge$from, character(1)))
  paths <- list()
  walk <- function(node_id, edge_path, visited) {
    outgoing <- adjacency[[node_id]]
    if (is.null(outgoing)) return(invisible(NULL))
    for (edge in outgoing) {
      if (edge$to %in% visited) next
      next_path <- c(edge_path, list(edge))
      if (identical(edge$to, y_id)) {
        if (length(next_path) > 1) {
          paths[[length(paths) + 1L]] <<- next_path
        }
      } else {
        walk(edge$to, next_path, c(visited, edge$to))
      }
    }
    invisible(NULL)
  }
  walk(x_id, list(), x_id)
  paths
}

rp_monomial_label <- function(power_w, power_z) {
  parts <- character(0)
  if (power_w > 0) {
    parts <- c(parts, if (power_w == 1) "W" else paste0("W^", power_w))
  }
  if (power_z > 0) {
    parts <- c(parts, if (power_z == 1) "Z" else paste0("Z^", power_z))
  }
  paste(parts, collapse = "_x_")
}

rp_moderator_grid <- function(node, original_values, centering_means) {
  if (is.null(node)) {
    return(list(model = 0, original = 0, labels = "fixed"))
  }
  values <- original_values[[node$id]]
  original <- as.numeric(quantile(
    values,
    probs = c(0.16, 0.50, 0.84),
    names = FALSE,
    type = 6
  ))
  labels <- c("percentile_16", "median", "percentile_84")
  center <- if (is.null(centering_means[[node$id]])) 0 else centering_means[[node$id]]
  list(model = original - center, original = original, labels = labels)
}

researchpath_bootstrap_effect_intervals <- function(
  values, effect_rows, definitions, interval_function,
  confidence_level, replicates, bootstrap_seed
) {
  invalid_total <- 0L
  for (index in seq_along(definitions)) {
    interval <- interval_function(values[, index], effect_rows[[index]]$estimate)
    invalid_total <- invalid_total + as.integer(interval$invalidReplicationCount %||% 0L)
    effect_rows[[index]]$standardError <- sd(interval$values)
    effect_rows[[index]]$confidenceInterval <- list(
      level = confidence_level,
      lower = interval$lower,
      upper = interval$upper,
      method = interval$method,
      replicates = replicates,
      seed = researchpath_seed(bootstrap_seed)
    )
  }
  list(effects = effect_rows, invalidReplicationCount = invalid_total)
}

researchpath_generic_process_effects <- function(
  spec, fits, plans, fit_key_by_outcome, x_node, y_node, w_node, z_node,
  original_values, centering_means, bootstrap_config, replicates, alpha,
  included_n
) {
  edge_by_id <- setNames(spec$edges, vapply(spec$edges, function(edge) edge$id, character(1)))
  moderation_by_edge <- split(
    spec$moderations,
    vapply(spec$moderations, function(item) item$targetEdgeId, character(1))
  )
  coefficient_sets <- lapply(fits, coef)

  edge_polynomial <- function(edge, coefficients = coefficient_sets) {
    fit_key <- fit_key_by_outcome[[edge$to]]
    polynomial <- list()
    polynomial <- rp_poly_add_term(
      polynomial, 0L, 0L, unname(coefficients[[fit_key]][[edge$from]])
    )
    edge_moderations <- moderation_by_edge[[edge$id]]
    if (is.null(edge_moderations)) return(polynomial)
    for (item in edge_moderations) {
      moderator_node <- Filter(
        function(node) identical(node$id, item$moderatorNodeId),
        spec$nodes
      )[[1]]
      if (!is.null(item$secondaryModeratorNodeId)) {
        polynomial <- rp_poly_add_term(
          polynomial, 1L, 1L,
          unname(coefficients[[fit_key]][[item$productTermId]])
        )
      } else if (identical(moderator_node$role, "w")) {
        polynomial <- rp_poly_add_term(
          polynomial, 1L, 0L,
          unname(coefficients[[fit_key]][[item$productTermId]])
        )
      } else if (identical(moderator_node$role, "z")) {
        polynomial <- rp_poly_add_term(
          polynomial, 0L, 1L,
          unname(coefficients[[fit_key]][[item$productTermId]])
        )
      }
    }
    polynomial
  }

  paths <- rp_indirect_paths(spec$edges, x_node$id, y_node$id)
  if (length(paths) == 0) {
    return(list(effects = list(), bootstrapParallel = NULL))
  }
  path_polynomials <- lapply(paths, function(path) {
    polynomial <- list("0,0" = 1)
    for (edge in path) {
      polynomial <- rp_poly_multiply(polynomial, edge_polynomial(edge))
    }
    polynomial
  })
  total_polynomial <- list()
  for (polynomial in path_polynomials) {
    total_polynomial <- rp_poly_add(total_polynomial, polynomial)
  }

  w_grid <- rp_moderator_grid(w_node, original_values, centering_means)
  z_grid <- rp_moderator_grid(z_node, original_values, centering_means)
  definitions <- list()
  effect_rows <- list()

  path_label <- function(path) {
    nodes <- c(path[[1]]$from, vapply(path, function(edge) edge$to, character(1)))
    paste(nodes, collapse = " -> ")
  }
  append_effect <- function(row, definition) {
    effect_rows[[length(effect_rows) + 1L]] <<- row
    definitions[[length(definitions) + 1L]] <<- definition
  }
  append_polynomial_effects <- function(polynomial, path_index = NULL, total = FALSE) {
    nonconstant_keys <- setdiff(names(polynomial), "0,0")
    # Keep the total indirect effect distinct from the total effect (c).
    # PROCESS reports both rows and the ResultBundle requires stable unique
    # identifiers; using ``effect_total`` for both silently overwrote one in
    # downstream exports.
    identifier <- if (total) "total_indirect" else paste0("path_", path_index)
    label_prefix <- if (total) {
      "total_indirect"
    } else {
      paste0("specific_indirect: ", path_label(paths[[path_index]]))
    }
    if (length(nonconstant_keys) == 0) {
      append_effect(
        list(
          id = paste0("effect_", identifier),
          type = "indirect",
          label = label_prefix,
          estimate = unname(polynomial[["0,0"]])
        ),
        list(kind = "value", pathIndex = path_index, total = total, w = 0, z = 0)
      )
      return(invisible(NULL))
    }

    powers <- lapply(nonconstant_keys, function(key) {
      as.integer(strsplit(key, ",", fixed = TRUE)[[1]])
    })
    uses_w <- any(vapply(powers, function(item) item[[1]] > 0, logical(1)))
    uses_z <- any(vapply(powers, function(item) item[[2]] > 0, logical(1)))
    w_indices <- if (uses_w) {
      seq_along(w_grid$model)
    } else if (length(w_grid$model) >= 2) {
      2L
    } else {
      1L
    }
    z_indices <- if (uses_z) {
      seq_along(z_grid$model)
    } else if (length(z_grid$model) >= 2) {
      2L
    } else {
      1L
    }
    for (w_index in w_indices) {
      for (z_index in z_indices) {
        condition_label <- paste(
          c(
            if (uses_w) paste0("W_", w_grid$labels[[w_index]]) else NULL,
            if (uses_z) paste0("Z_", z_grid$labels[[z_index]]) else NULL
          ),
          collapse = "__"
        )
        append_effect(
          list(
            id = paste0("effect_", identifier, "_conditional_", condition_label),
            type = "conditional",
            label = paste0(label_prefix, " @ ", condition_label),
            estimate = unname(rp_poly_evaluate(
              polynomial, w_grid$model[[w_index]], z_grid$model[[z_index]]
            ))
          ),
          list(
            kind = "value", pathIndex = path_index, total = total,
            w = w_grid$model[[w_index]], z = z_grid$model[[z_index]]
          )
        )
      }
    }
    for (key in nonconstant_keys) {
      monomial <- as.integer(strsplit(key, ",", fixed = TRUE)[[1]])
      monomial_label <- rp_monomial_label(monomial[[1]], monomial[[2]])
      append_effect(
        list(
          id = paste0("effect_", identifier, "_index_", gsub("\\^", "", monomial_label)),
          type = "index",
          label = paste0(label_prefix, " · polynomial index ", monomial_label),
          estimate = unname(polynomial[[key]])
        ),
        list(
          kind = "coefficient", pathIndex = path_index, total = total,
          powerW = monomial[[1]], powerZ = monomial[[2]]
        )
      )
    }
    invisible(NULL)
  }

  for (path_index in seq_along(path_polynomials)) {
    append_polynomial_effects(path_polynomials[[path_index]], path_index, FALSE)
  }
  append_polynomial_effects(total_polynomial, NULL, TRUE)

  controls_y <- character(0)
  for (assignment in spec$covariates) {
    if (y_node$id %in% unlist(assignment$outcomeNodeIds)) {
      controls_y <- c(controls_y, assignment$nodeId)
    }
  }
  total_fit <- fit_plan(
    analysis_data,
    list(outcome = y_node$id, predictors = unique(c(x_node$id, controls_y)))
  )
  effect_rows[[length(effect_rows) + 1L]] <- list(
    id = "effect_total",
    type = "total",
    label = "c",
    estimate = unname(coef(total_fit)[[x_node$id]])
  )

  if (!isTRUE(bootstrap_config$enabled) || replicates <= 0) {
    return(list(effects = effect_rows, bootstrapParallel = NULL))
  }

  designs <- lapply(fits, function(fit) {
    list(
      x = model.matrix(fit),
      y = model.response(model.frame(fit)),
      binary = inherits(fit, "glm")
    )
  })
  edge_terms <- lapply(spec$edges, function(edge) {
    items <- moderation_by_edge[[edge$id]]
    terms <- list()
    if (!is.null(items)) {
      for (item in items) {
        moderator_node <- Filter(
          function(node) identical(node$id, item$moderatorNodeId),
          spec$nodes
        )[[1]]
        powers <- if (!is.null(item$secondaryModeratorNodeId)) {
          c(1L, 1L)
        } else if (identical(moderator_node$role, "w")) {
          c(1L, 0L)
        } else {
          c(0L, 1L)
        }
        terms[[length(terms) + 1L]] <- list(
          term = item$productTermId,
          powerW = powers[[1]],
          powerZ = powers[[2]]
        )
      }
    }
    list(
      id = edge$id,
      fitKey = fit_key_by_outcome[[edge$to]],
      baseTerm = edge$from,
      terms = terms
    )
  })
  names(edge_terms) <- vapply(edge_terms, function(item) item$id, character(1))
  path_edge_ids <- lapply(paths, function(path) {
    vapply(path, function(edge) edge$id, character(1))
  })

  callback_environment <- list2env(
    list(
      designs = designs,
      edgeTerms = edge_terms,
      pathEdgeIds = path_edge_ids,
      definitions = definitions,
      sampleSize = included_n,
      outputColumns = length(definitions),
      polyAddTerm = rp_poly_add_term,
      polyAdd = rp_poly_add,
      polyMultiply = rp_poly_multiply,
      polyEvaluate = rp_poly_evaluate,
      researchpath_seed = researchpath_seed
    ),
    parent = globalenv()
  )
  callback <- eval(quote(function(replicate_seed) {
    tryCatch({
      set.seed(researchpath_seed(replicate_seed))
      indices <- sample.int(sampleSize, sampleSize, replace = TRUE)
      fitted <- lapply(designs, function(design) {
        x <- design$x[indices, , drop = FALSE]
        y <- design$y[indices]
        if (isTRUE(design$binary)) {
          fit <- suppressWarnings(stats::glm.fit(
            x = x, y = y, family = stats::binomial(link = "logit")
          ))
          if (!isTRUE(fit$converged) || any(!is.finite(fit$coefficients))) {
            stop("invalid bootstrap logistic fit")
          }
          fit$coefficients
        } else {
          stats::lm.fit(x = x, y = y)$coefficients
        }
      })
      edge_polynomials <- lapply(edgeTerms, function(edge) {
        polynomial <- list()
        polynomial <- polyAddTerm(
          polynomial, 0L, 0L,
          unname(fitted[[edge$fitKey]][[edge$baseTerm]])
        )
        for (term in edge$terms) {
          polynomial <- polyAddTerm(
            polynomial, term$powerW, term$powerZ,
            unname(fitted[[edge$fitKey]][[term$term]])
          )
        }
        polynomial
      })
      path_polynomials <- lapply(pathEdgeIds, function(edge_ids) {
        polynomial <- list("0,0" = 1)
        for (edge_id in edge_ids) {
          polynomial <- polyMultiply(polynomial, edge_polynomials[[edge_id]])
        }
        polynomial
      })
      total_polynomial <- list()
      for (polynomial in path_polynomials) {
        total_polynomial <- polyAdd(total_polynomial, polynomial)
      }
      vapply(definitions, function(definition) {
        polynomial <- if (isTRUE(definition$total)) {
          total_polynomial
        } else {
          path_polynomials[[definition$pathIndex]]
        }
        if (identical(definition$kind, "coefficient")) {
          key <- paste0(definition$powerW, ",", definition$powerZ)
          if (key %in% names(polynomial)) polynomial[[key]] else 0
        } else {
          polyEvaluate(polynomial, definition$w, definition$z)
        }
      }, numeric(1))
    }, error = function(error) rep(NA_real_, outputColumns))
  }), envir = callback_environment)

  bootstrap_parallel <- researchpath_parallel_profile(replicates)
  work_units <- as.double(replicates) * as.double(included_n) * as.double(length(plans))
  if (!researchpath_use_parallel(work_units, replicates)) {
    bootstrap_parallel$backend <- "sequential"
    bootstrap_parallel$workers <- 1L
  }
  values <- matrix(NA_real_, nrow = replicates, ncol = length(definitions))
  set.seed(researchpath_seed(bootstrap_config$seed))
  replicate_seeds <- sample.int(.Machine$integer.max, replicates, replace = TRUE)
  chunks <- researchpath_parallel_chunks(replicates, 1L, tasks_per_worker = 5000L)
  for (chunk in chunks) {
    check_cancel()
    chunk_values <- researchpath_parallel_grouped_lapply(
      as.list(replicate_seeds[chunk]), callback, bootstrap_parallel$workers
    )
    for (offset in seq_along(chunk)) {
      values[chunk[[offset]], ] <- chunk_values[[offset]]
    }
    completed <- max(chunk)
    write_progress(
      "bootstrapping", 0.25 + 0.65 * completed / replicates,
      completed, replicates
    )
  }
  intervals <- researchpath_bootstrap_effect_intervals(
    values, effect_rows, definitions, bootstrap_interval,
    spec$estimation$confidenceLevel, replicates, bootstrap_config$seed
  )
  list(
    effects = intervals$effects,
    bootstrapParallel = bootstrap_parallel,
    invalidReplicationCount = intervals$invalidReplicationCount
  )
}
