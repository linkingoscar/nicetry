positive_definite_covariance <- function(matrix_value, floor_value = 1e-8) {
  matrix_value <- (matrix_value + t(matrix_value)) / 2
  decomposition <- eigen(matrix_value, symmetric = TRUE)
  values <- pmax(decomposition$values, floor_value)
  decomposition$vectors %*% diag(values, nrow = length(values)) %*%
    t(decomposition$vectors)
}

little_mcar_diagnostic <- function(frame, variable_ids, label_lookup) {
  usable_ids <- variable_ids[vapply(variable_ids, function(id) {
    values <- frame[[id]]
    sum(is.finite(values)) >= 3L &&
      length(unique(values[is.finite(values)])) > 1L
  }, logical(1))]
  if (length(usable_ids) < 2L) {
    return(list(available = FALSE, reason = "Little MCAR 检验至少需要两个有变异的数值变量"))
  }
  if (length(usable_ids) > 20L) {
    return(list(available = FALSE, reason = "Little MCAR 检验当前最多支持 20 个数值变量"))
  }
  matrix_data <- as.matrix(frame[, usable_ids, drop = FALSE])
  storage.mode(matrix_data) <- "double"
  if (!any(!is.finite(matrix_data))) {
    return(list(available = FALSE, reason = "所选数值变量没有缺失值"))
  }
  matrix_data[!is.finite(matrix_data)] <- NA_real_
  keep_rows <- rowSums(!is.na(matrix_data)) > 0L
  matrix_data <- matrix_data[keep_rows, , drop = FALSE]
  n <- nrow(matrix_data)
  p <- ncol(matrix_data)
  if (n <= p + 2L) {
    return(list(available = FALSE, reason = "Little MCAR 检验的有效行数不足"))
  }

  location <- colMeans(matrix_data, na.rm = TRUE)
  filled <- matrix_data
  for (column in seq_len(p)) {
    filled[is.na(filled[, column]), column] <- location[[column]]
  }
  covariance <- positive_definite_covariance(cov(filled), 1e-6)
  converged <- FALSE
  iterations <- 0L
  for (iteration in seq_len(200L)) {
    sum_x <- numeric(p)
    sum_xx <- matrix(0, p, p)
    for (row_index in seq_len(n)) {
      observed <- which(!is.na(matrix_data[row_index, ]))
      missing <- setdiff(seq_len(p), observed)
      expected <- location
      if (length(observed) > 0L) {
        expected[observed] <- matrix_data[row_index, observed]
      }
      conditional_covariance <- matrix(0, length(missing), length(missing))
      if (length(missing) > 0L) {
        if (length(observed) > 0L) {
          observed_inverse <- tryCatch(
            solve(covariance[observed, observed, drop = FALSE]),
            error = function(error) qr.solve(
              covariance[observed, observed, drop = FALSE]
            )
          )
          expected[missing] <- location[missing] +
            covariance[missing, observed, drop = FALSE] %*% observed_inverse %*%
              (matrix_data[row_index, observed] - location[observed])
          conditional_covariance <- covariance[missing, missing, drop = FALSE] -
            covariance[missing, observed, drop = FALSE] %*% observed_inverse %*%
              covariance[observed, missing, drop = FALSE]
        } else {
          conditional_covariance <- covariance
        }
      }
      second_moment <- tcrossprod(expected)
      if (length(missing) > 0L) {
        second_moment[missing, missing] <- second_moment[missing, missing] +
          conditional_covariance
      }
      sum_x <- sum_x + expected
      sum_xx <- sum_xx + second_moment
    }
    next_location <- sum_x / n
    next_covariance <- positive_definite_covariance(
      sum_xx / n - tcrossprod(next_location), 1e-8
    )
    difference <- max(
      abs(next_location - location),
      abs(next_covariance - covariance)
    )
    location <- next_location
    covariance <- next_covariance
    iterations <- iteration
    if (difference < 1e-7) {
      converged <- TRUE
      break
    }
  }

  pattern_keys <- apply(!is.na(matrix_data), 1, paste0, collapse = "")
  statistic <- 0
  observed_dimension_sum <- 0L
  for (pattern in unique(pattern_keys)) {
    rows <- which(pattern_keys == pattern)
    observed <- which(!is.na(matrix_data[rows[[1]], ]))
    if (length(observed) == 0L) next
    pattern_mean <- colMeans(
      matrix_data[rows, observed, drop = FALSE], na.rm = TRUE
    )
    difference <- pattern_mean - location[observed]
    inverse <- tryCatch(
      solve(covariance[observed, observed, drop = FALSE]),
      error = function(error) qr.solve(covariance[observed, observed, drop = FALSE])
    )
    statistic <- statistic + length(rows) * as.numeric(
      t(difference) %*% inverse %*% difference
    )
    observed_dimension_sum <- observed_dimension_sum + length(observed)
  }
  degrees_of_freedom <- observed_dimension_sum - p
  if (degrees_of_freedom <= 0L || !is.finite(statistic)) {
    return(list(available = FALSE, reason = "缺失模式不足以形成正自由度的 Little MCAR 检验"))
  }
  list(
    available = TRUE,
    statistic = finite_number(statistic),
    degreesOfFreedom = degrees_of_freedom,
    pValue = finite_number(pchisq(statistic, degrees_of_freedom, lower.tail = FALSE)),
    variableIds = as.list(usable_ids),
    variableLabels = as.list(vapply(usable_ids, label_lookup, character(1))),
    n = n,
    patternCount = length(unique(pattern_keys)),
    emConverged = converged,
    emIterations = iterations,
    method = "Little MCAR test with multivariate-normal EM estimates"
  )
}

build_missing_data_report <- function(data, report_ids, mcar_ids, label_lookup) {
  report_ids <- unique(report_ids[report_ids %in% names(data)])
  total <- nrow(data)
  missing_matrix <- sapply(report_ids, function(id) {
    values <- data[[id]]
    is.na(values) | trimws(as.character(values)) == ""
  })
  if (is.null(dim(missing_matrix))) {
    missing_matrix <- matrix(missing_matrix, ncol = 1L)
  }
  colnames(missing_matrix) <- report_ids
  variables <- lapply(report_ids, function(id) {
    missing_count <- sum(missing_matrix[, id])
    list(
      id = id,
      label = label_lookup(id),
      validCount = total - missing_count,
      missingCount = missing_count,
      missingRate = finite_number(missing_count / total)
    )
  })
  keys <- apply(missing_matrix, 1, function(row) {
    paste0(as.integer(row), collapse = "")
  })
  key_counts <- sort(table(keys), decreasing = TRUE)
  pattern_limit <- min(20L, length(key_counts))
  patterns <- lapply(seq_len(pattern_limit), function(index) {
    key <- names(key_counts)[[index]]
    missing_ids <- report_ids[strsplit(key, "", fixed = TRUE)[[1]] == "1"]
    list(
      missingIds = as.list(missing_ids),
      missingLabels = as.list(vapply(missing_ids, label_lookup, character(1))),
      count = as.integer(key_counts[[index]]),
      proportion = finite_number(as.integer(key_counts[[index]]) / total)
    )
  })
  list(
    rowCount = total,
    variableCount = length(report_ids),
    completeCaseCount = sum(rowSums(missing_matrix) == 0L),
    incompleteCaseCount = sum(rowSums(missing_matrix) > 0L),
    anyMissingCellCount = sum(missing_matrix),
    variables = variables,
    patterns = patterns,
    patternCount = length(key_counts),
    patternsTruncated = length(key_counts) > pattern_limit,
    littleMcar = little_mcar_diagnostic(data, mcar_ids, label_lookup),
    guidance = "Little MCAR 仅检验 MCAR 与数据的相容性；不显著不证明 MCAR，显著也不能区分 MAR 与 MNAR。"
  )
}
