# ResearchPath R Engine - Experimental Protocol & Manipulation Check (WP-EXP-01)

run_manipulation_check <- function(data, dv, group_var) {
  if (!dv %in% colnames(data)) {
    stop(paste("操纵检查因变量不存在:", dv))
  }
  if (!group_var %in% colnames(data)) {
    stop(paste("分组变量不存在:", group_var))
  }

  sub_df <- data[!is.na(data[[dv]]) & !is.na(data[[group_var]]), ]
  group_factor <- as.factor(sub_df[[group_var]])
  levels_count <- length(levels(group_factor))

  if (levels_count < 2) {
    stop("操纵检查需要至少 2 个实验分组")
  }

  formula_obj <- as.formula(paste(dv, "~", group_var))
  fit <- aov(formula_obj, data = sub_df)
  fit_summary <- summary(fit)[[1]]

  p_val <- as.numeric(fit_summary["Pr(>F)"][1, 1])
  f_stat <- as.numeric(fit_summary["F value"][1, 1])
  df1 <- as.numeric(fit_summary["Df"][1])
  df2 <- as.numeric(fit_summary["Df"][2])

  ss_between <- fit_summary["Sum Sq"][1, 1]
  ss_total <- sum(fit_summary["Sum Sq"])
  eta_sq <- as.numeric(ss_between / ss_total)

  means <- tapply(sub_df[[dv]], group_factor, mean, na.rm = TRUE)
  sds <- tapply(sub_df[[dv]], group_factor, sd, na.rm = TRUE)
  ns <- tapply(sub_df[[dv]], group_factor, length)

  group_stats <- lapply(names(means), function(g) {
    list(
      group = g,
      n = as.integer(ns[[g]]),
      mean = round(as.numeric(means[[g]]), 4),
      sd = round(as.numeric(sds[[g]]), 4)
    )
  })

  passed <- p_val < 0.05

  list(
    dv = dv,
    groupVariable = group_var,
    fStatistic = round(f_stat, 4),
    df1 = df1,
    df2 = df2,
    pValue = round(p_val, 6),
    etaSquared = round(eta_sq, 4),
    manipulationSuccessful = passed,
    groupStats = group_stats
  )
}

check_baseline_balance <- function(data, baseline_vars, group_var) {
  if (!group_var %in% colnames(data)) {
    stop(paste("分组变量不存在:", group_var))
  }

  results <- lapply(baseline_vars, function(var) {
    if (!var %in% colnames(data)) {
      return(list(variable = var, status = "missing"))
    }

    vec <- data[[var]]
    if (is.numeric(vec)) {
      fit <- aov(as.formula(paste(var, "~", group_var)), data = data)
      s <- summary(fit)[[1]]
      p_val <- as.numeric(s["Pr(>F)"][1, 1])
      f_val <- as.numeric(s["F value"][1, 1])
      list(
        variable = var,
        type = "continuous",
        statistic = round(f_val, 4),
        pValue = round(p_val, 4),
        balanced = p_val >= 0.05
      )
    } else {
      tbl <- table(data[[var]], data[[group_var]])
      test <- chisq.test(tbl)
      list(
        variable = var,
        type = "categorical",
        statistic = round(as.numeric(test$statistic), 4),
        pValue = round(as.numeric(test$p.value), 4),
        balanced = as.numeric(test$p.value) >= 0.05
      )
    }
  })

  list(
    groupVariable = group_var,
    overallBalanced = all(sapply(results, function(r) isTRUE(r$balanced))),
    variables = results
  )
}

# ---------------------------------------------------------------------------
# CONSORT Flow Diagram Data Generation (WP-CORE-E-01)
# ---------------------------------------------------------------------------

generate_consort_flow_data <- function(data, dv, group_var = NULL) {
  n_total <- nrow(data)
  relevant_cols <- c(dv, group_var)
  relevant_cols <- relevant_cols[!is.null(relevant_cols) & relevant_cols %in% names(data)]

  complete_mask <- complete.cases(data[, relevant_cols, drop = FALSE])
  n_analyzed <- sum(complete_mask)
  n_excluded <- n_total - n_analyzed

  group_allocation <- if (!is.null(group_var) && group_var %in% names(data)) {
    tbl <- table(data[[group_var]][complete_mask])
    lapply(names(tbl), function(g) list(group = g, nAllocated = as.integer(tbl[[g]]), nAnalyzed = as.integer(tbl[[g]])))
  } else list()

  list(
    available = TRUE,
    enrollment = list(screened = as.integer(n_total), excluded = as.integer(n_excluded), randomized = as.integer(n_analyzed)),
    allocation = group_allocation,
    followUp = list(lostToFollowUp = 0L, discontinued = 0L),
    analysis = list(analyzed = as.integer(n_analyzed), excludedFromAnalysis = 0L)
  )
}

