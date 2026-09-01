build_empirical_paper_summary <- function(
  correlation_ids, descriptives, construct_validity, construct_score_ids,
  count_matrix, coefficient_matrix, p_value_matrix, raw_p_value_matrix,
  adjusted_p_value_matrix, ci_lower_matrix, ci_upper_matrix,
  method_label, multiplicity, label_for, confidence_level = 0.95
) {
  validity_by_score <- setNames(construct_validity, construct_score_ids)
  descriptives_by_id <- setNames(descriptives, vapply(descriptives, function(row) row$id, character(1)))
  rows <- lapply(seq_along(correlation_ids), function(index) {
    id <- correlation_ids[[index]]
    descriptive <- descriptives_by_id[[id]]
    reliability <- validity_by_score[[id]]
    list(
      id = id, label = label_for(id),
      n = if (is.null(descriptive)) count_matrix[index, index] else descriptive$n,
      mean = if (is.null(descriptive)) NA_real_ else descriptive$mean,
      sd = if (is.null(descriptive)) NA_real_ else descriptive$sd,
      alpha = if (is.null(reliability)) NA_real_ else reliability$alpha,
      omega = if (is.null(reliability)) NA_real_ else reliability$omega,
      correlations = as.list(coefficient_matrix[index, ]),
      pValues = as.list(p_value_matrix[index, ]),
      pValuesRaw = as.list(raw_p_value_matrix[index, ]),
      pValuesAdjusted = as.list(adjusted_p_value_matrix[index, ]),
      counts = as.list(count_matrix[index, ]),
      ciLower = as.list(ci_lower_matrix[index, ]),
      ciUpper = as.list(ci_upper_matrix[index, ])
    )
  })
  list(
    title = "Descriptive statistics, reliability, and correlations",
    variables = lapply(correlation_ids, function(id) list(id = id, label = label_for(id))),
    rows = rows, correlationMethod = method_label, confidenceLevel = confidence_level,
    pValueDisplay = "adjusted", multiplicity = multiplicity
  )
}

build_empirical_aggregation_diagnostics <- function(data, options, constructs, label_for) {
  if (is.null(options$aggregationVariableId) || options$aggregationVariableId == "") return(NULL)
  aggregation_id <- options$aggregationVariableId
  list(
    groupVariableId = aggregation_id,
    groupLabel = label_for(aggregation_id),
    method = "one-way random-effects ANOVA and rectangular-null rwg(j)",
    constructs = lapply(constructs, function(construct) {
      calc_aggregation_diagnostics(
        data = data, outcome_id = construct$scoreId, outcome_label = construct$label,
        cluster_id = aggregation_id,
        scale_min = as.numeric(construct$theoreticalMinimum),
        scale_max = as.numeric(construct$theoreticalMaximum),
        item_count = as.integer(construct$itemCount),
        aggregation_method = construct$aggregation
      )
    }),
    guidance = paste(
      "ICC(1)、ICC(2)、设计效应与 rwg(j) 仅提供聚合诊断；",
      "不使用固定阈值自动宣布可聚合。"
    )
  )
}

fit_empirical_group_comparison <- function(
  data, options, scale_ids, label_for, finite_number, non_iid_context,
  confidence_level = 0.95, multiplicity_family_id = "cross_sectional_inference"
) {
  if (
    non_iid_context || is.null(options$groupVariableId) ||
    options$groupVariableId == ""
  ) return(NULL)
  group_id <- options$groupVariableId
  group_values <- as.factor(data[[group_id]])
  usable_levels <- levels(droplevels(group_values[!is.na(group_values)]))
  if (length(usable_levels) < 2 || length(usable_levels) > 10) return(NULL)

  comparison_results <- lapply(scale_ids, function(scale_id) {
    frame <- data.frame(outcome = data[[scale_id]], group = group_values)
    frame <- frame[complete.cases(frame), , drop = FALSE]
    frame$group <- droplevels(frame$group)
    summaries <- lapply(levels(frame$group), function(level) {
      values <- frame$outcome[frame$group == level]
      list(level = level, n = length(values), mean = finite_number(mean(values)), sd = finite_number(sd(values)))
    })
    tryCatch({
      if (nlevels(frame$group) == 2) {
        test <- t.test(outcome ~ group, data = frame)
        groups <- split(frame$outcome, frame$group)
        pooled_sd <- sqrt(
          ((length(groups[[1]]) - 1) * var(groups[[1]]) +
            (length(groups[[2]]) - 1) * var(groups[[2]])) / (nrow(frame) - 2)
        )
        cohen_d <- (mean(groups[[2]]) - mean(groups[[1]])) / pooled_sd
        correction <- 1 - 3 / (4 * (nrow(frame) - 2) - 1)
        effect <- correction * cohen_d
        effect_standard_error <- correction * sqrt(
          (length(groups[[1]]) + length(groups[[2]])) /
            (length(groups[[1]]) * length(groups[[2]])) +
            cohen_d^2 / (2 * (length(groups[[1]]) + length(groups[[2]]) - 2))
        )
        effect_interval <- effect + c(-1, 1) * qnorm(1 - (1 - confidence_level) / 2) * effect_standard_error
        list(
          id = scale_id, label = label_for(scale_id), test = "Welch independent-samples t",
          statistic = finite_number(unname(test$statistic)),
          df1 = finite_number(unname(test$parameter)), df2 = NA_real_,
          pValue = finite_number(test$p.value), effectSize = finite_number(effect),
          effectSizeCiLower = finite_number(effect_interval[[1]]),
          effectSizeCiUpper = finite_number(effect_interval[[2]]),
          effectSizeConfidenceLevel = confidence_level,
          effectSizeCiMethod = "normal approximation using the small-sample-corrected standardized mean-difference SE",
          effectSizeType = "Hedges g (group 2 minus group 1; pooled-SD, small-sample corrected)",
          groups = summaries
        )
      } else {
        fit <- aov(outcome ~ group, data = frame)
        table <- summary(fit)[[1]]
        effect <- table[1, "Sum Sq"] / sum(table[, "Sum Sq"])
        mean_square_error <- table[2, "Mean Sq"]
        omega_squared <- (table[1, "Sum Sq"] - table[1, "Df"] * mean_square_error) /
          (sum(table[, "Sum Sq"]) + mean_square_error)
        absolute_deviation <- ave(frame$outcome, frame$group, FUN = function(values) abs(values - median(values)))
        brown_forsythe_table <- summary(aov(absolute_deviation ~ frame$group))[[1]]
        welch_test <- oneway.test(outcome ~ group, data = frame, var.equal = FALSE)

        tukey_table <- tryCatch(
          TukeyHSD(fit, conf.level = confidence_level)$group,
          error = function(e) NULL
        )
        pairwise_tukey <- list()
        if (!is.null(tukey_table)) {
          for (index in seq_len(nrow(tukey_table))) {
            pairwise_tukey[[length(pairwise_tukey) + 1]] <- list(
              comparison = rownames(tukey_table)[index],
              difference = finite_number(as.numeric(tukey_table[index, "diff"])),
              lower = finite_number(as.numeric(tukey_table[index, "lwr"])),
              upper = finite_number(as.numeric(tukey_table[index, "upr"])),
              pValue = finite_number(as.numeric(tukey_table[index, "p adj"])),
              confidenceLevel = confidence_level
            )
          }
        }

        bonferroni <- tryCatch(
          pairwise.t.test(frame$outcome, frame$group, p.adjust.method = "bonferroni"),
          error = function(e) NULL
        )
        pairwise_bonferroni <- list()
        if (!is.null(bonferroni) && !is.null(bonferroni$p.value)) {
          p_matrix <- bonferroni$p.value
          for (column_index in seq_len(ncol(p_matrix))) {
            for (row_index in seq_len(nrow(p_matrix))) {
              p_value <- p_matrix[row_index, column_index]
              if (!is.na(p_value)) {
                pairwise_bonferroni[[length(pairwise_bonferroni) + 1]] <- list(
                  comparison = paste0(rownames(p_matrix)[row_index], "-", colnames(p_matrix)[column_index]),
                  pValue = finite_number(as.numeric(p_value))
                )
              }
            }
          }
        }

        pairwise_games_howell <- list()
        group_split <- split(frame$outcome, frame$group)
        group_names <- names(group_split)
        for (left_index in seq_len(length(group_names) - 1)) {
          for (right_index in seq.int(left_index + 1, length(group_names))) {
            left <- group_split[[left_index]]; right <- group_split[[right_index]]
            left_component <- var(left) / length(left); right_component <- var(right) / length(right)
            standard_error <- sqrt(left_component + right_component)
            degrees <- (left_component + right_component)^2 / (
              left_component^2 / (length(left) - 1) + right_component^2 / (length(right) - 1)
            )
            difference <- mean(right) - mean(left)
            q_statistic <- sqrt(2) * abs(difference) / standard_error
            critical <- qtukey(
              confidence_level,
              nmeans = length(group_names),
              df = degrees
            ) / sqrt(2)
            pairwise_games_howell[[length(pairwise_games_howell) + 1]] <- list(
              comparison = paste0(group_names[[right_index]], "-", group_names[[left_index]]),
              difference = finite_number(difference), standardError = finite_number(standard_error),
              degreesOfFreedom = finite_number(degrees),
              lower = finite_number(difference - critical * standard_error),
              upper = finite_number(difference + critical * standard_error),
              confidenceLevel = confidence_level,
              pValue = finite_number(ptukey(
                q_statistic, nmeans = length(group_names), df = degrees, lower.tail = FALSE
              ))
            )
          }
        }
        list(
          id = scale_id, label = label_for(scale_id), test = "one-way ANOVA",
          statistic = finite_number(table[1, "F value"]),
          df1 = finite_number(table[1, "Df"]), df2 = finite_number(table[2, "Df"]),
          pValue = finite_number(table[1, "Pr(>F)"]), effectSize = finite_number(effect),
          effectSizeType = "eta squared", omegaSquared = finite_number(omega_squared),
          confidenceLevel = confidence_level,
          groups = summaries,
          assumptionTests = list(brownForsythe = list(
            statistic = finite_number(brown_forsythe_table[1, "F value"]),
            df1 = finite_number(brown_forsythe_table[1, "Df"]),
            df2 = finite_number(brown_forsythe_table[2, "Df"]),
            pValue = finite_number(brown_forsythe_table[1, "Pr(>F)"])
          )),
          robustTest = list(
            method = "Welch one-way ANOVA",
            statistic = finite_number(unname(welch_test$statistic)),
            df1 = finite_number(unname(welch_test$parameter[[1]])),
            df2 = finite_number(unname(welch_test$parameter[[2]])),
            pValue = finite_number(welch_test$p.value),
            role = "sensitivity"
          ),
          pairwiseTukey = pairwise_tukey,
          pairwiseBonferroni = pairwise_bonferroni,
          pairwiseGamesHowell = pairwise_games_howell
        )
      }
    }, error = function(error) list(
      id = scale_id, label = label_for(scale_id), unavailable = TRUE,
      reason = paste0("组间比较因样本不足或组内零方差无法估计：", conditionMessage(error)),
      test = NA_character_, statistic = NA_real_, df1 = NA_real_, df2 = NA_real_,
      pValue = NA_real_, effectSize = NA_real_, effectSizeType = NA_character_,
      groups = summaries
    ))
  })

  group_adjustment <- if (
    !is.null(options$groupOmnibusPAdjust) &&
    options$groupOmnibusPAdjust %in% c("none", "holm", "BH")
  ) options$groupOmnibusPAdjust else "holm"
  primary_raw <- vapply(comparison_results, function(row) {
    if (isTRUE(row$unavailable) || is.null(row$pValue)) NA_real_ else as.numeric(row$pValue)
  }, numeric(1))
  robust_raw <- vapply(comparison_results, function(row) {
    if (is.null(row$robustTest$pValue)) NA_real_ else as.numeric(row$robustTest$pValue)
  }, numeric(1))
  assumption_raw <- vapply(comparison_results, function(row) {
    if (is.null(row$assumptionTests$brownForsythe$pValue)) NA_real_ else as.numeric(row$assumptionTests$brownForsythe$pValue)
  }, numeric(1))
  adjust_family <- function(values) {
    adjusted <- rep(NA_real_, length(values))
    finite <- which(is.finite(values))
    if (length(finite) > 0L) adjusted[finite] <- p.adjust(values[finite], method = group_adjustment)
    list(values = adjusted, size = as.integer(length(finite)))
  }
  primary_adjusted <- adjust_family(primary_raw)
  robust_adjusted <- adjust_family(robust_raw)
  assumption_adjusted <- adjust_family(assumption_raw)
  for (index in seq_along(comparison_results)) {
    row <- comparison_results[[index]]
    row$pValueRaw <- finite_number(primary_raw[[index]])
    row$pValueAdjusted <- finite_number(primary_adjusted$values[[index]])
    row$pValue <- row$pValueAdjusted
    row$multiplicityFamilyId <- "group_omnibus_across_constructs"
    row$multiplicityFamilySize <- primary_adjusted$size
    row$pAdjustMethod <- group_adjustment
    if (!is.null(row$robustTest)) {
      row$robustTest$pValueRaw <- finite_number(robust_raw[[index]])
      row$robustTest$pValueAdjusted <- finite_number(robust_adjusted$values[[index]])
      row$robustTest$pValue <- row$robustTest$pValueAdjusted
      row$robustTest$multiplicityFamilyId <- "group_welch_omnibus_across_constructs"
    }
    if (!is.null(row$assumptionTests$brownForsythe)) {
      row$assumptionTests$brownForsythe$pValueRaw <- finite_number(assumption_raw[[index]])
      row$assumptionTests$brownForsythe$pValueAdjusted <- finite_number(assumption_adjusted$values[[index]])
      row$assumptionTests$brownForsythe$pValue <- row$assumptionTests$brownForsythe$pValueAdjusted
      row$assumptionTests$brownForsythe$multiplicityFamilyId <- "brown_forsythe_across_constructs"
    }
    comparison_results[[index]] <- row
  }
  list(
    groupVariableId = group_id, groupLabel = label_for(group_id), levels = as.list(usable_levels),
    analysisPolicy = list(
      primaryModel = if (length(usable_levels) == 2L) "Welch independent-samples t" else "classical one-way ANOVA",
      sensitivityModel = if (length(usable_levels) == 2L) "HC3/heteroskedasticity diagnostic" else "Welch one-way ANOVA",
      selectionRule = "主模型在运行前声明；不根据 p 值、Brown–Forsythe 或结果显著性自动切换。",
      brownForsytheRole = "diagnostic_only"
    ),
    multiplicity = list(
      adjustment = group_adjustment,
      familyId = multiplicity_family_id,
      scope = "cross-sectional correlation, group comparison, regression and hypothesis evidence ledger",
      globalAdjustmentApplied = FALSE,
      primaryFamilyId = "group_omnibus_across_constructs",
      primaryFamilySize = primary_adjusted$size,
      robustFamilyId = "group_welch_omnibus_across_constructs",
      robustFamilySize = robust_adjusted$size,
      assumptionFamilyId = "brown_forsythe_across_constructs",
      assumptionFamilySize = assumption_adjusted$size,
      pairwiseScope = "within each construct; Tukey, Bonferroni, or Games-Howell adjusted procedures",
      confidenceIntervalsAdjustedAcrossConstructs = FALSE
    ),
    results = comparison_results
  )
}
