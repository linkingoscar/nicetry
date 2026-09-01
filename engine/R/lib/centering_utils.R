# Shared utility functions for centering variables in multilevel models

#' Person-mean centering
center_cwc <- function(data, var, id_var) {
  subject_values <- as.character(data[[id_var]])
  person_means <- tapply(data[[var]], subject_values, mean, na.rm = TRUE)
  grand_mean <- mean(person_means, na.rm = TRUE)
  person_mean <- unname(person_means[subject_values])
  within_name <- paste0(var, "__within")
  between_name <- paste0(var, "__between")
  data[[within_name]] <- data[[var]] - person_mean
  data[[between_name]] <- person_mean - grand_mean
  list(data = data, within = within_name, between = between_name, grand_mean = grand_mean)
}

#' Grand-mean centering
center_cgm <- function(data, var) {
  grand_mean <- mean(data[[var]], na.rm = TRUE)
  centered_name <- paste0(var, "__centered")
  data[[centered_name]] <- data[[var]] - grand_mean
  list(data = data, centered = centered_name, grand_mean = grand_mean)
}

#' Center a predictor based on the model spec
center_predictor <- function(data, spec) {
  predictor <- spec$predictorVariableId
  subject <- spec$subjectVariableId
  if (identical(spec$centering, "person_mean")) {
    res <- center_cwc(data, predictor, subject)
    return(list(
      data = res$data,
      within = res$within,
      between = res$between,
      protocol = list(
        strategy = "CWC_with_contextual_effect",
        level1Formula = paste0(predictor, "_it - mean_i(", predictor, ")"),
        level2Formula = paste0("mean_i(", predictor, ") - mean_person(mean_i(", predictor, "))"),
        personMeanReintroduced = TRUE,
        grandMeanWeighting = "equal weight per person",
        level1Reference = 0,
        level2Reference = ensure_finite(res$grand_mean)
      )
    ))
  }
  if (identical(spec$centering, "grand_mean")) {
    res <- center_cgm(data, predictor)
    return(list(
      data = res$data,
      within = res$centered,
      between = NULL,
      protocol = list(
        strategy = "CGM_observation_level",
        level1Formula = paste0(predictor, "_it - mean_observation(", predictor, ")"),
        level2Formula = NULL,
        personMeanReintroduced = FALSE,
        grandMeanWeighting = "equal weight per observation",
        level1Reference = ensure_finite(res$grand_mean),
        level2Reference = NULL
      )
    ))
  }
  list(
    data = data,
    within = predictor,
    between = NULL,
    protocol = list(
      strategy = "raw_uncentered",
      level1Formula = predictor,
      level2Formula = NULL,
      personMeanReintroduced = FALSE,
      grandMeanWeighting = NULL,
      level1Reference = 0,
      level2Reference = NULL
    )
  )
}

#' Generate metadata manifest describing what centering was applied
centering_manifest <- function(spec, centered, temporal) {
  interpretation <- switch(
    centered$protocol$strategy,
    CWC_with_contextual_effect = paste0(
      "Level-1 的 CWC 系数表示同一被试相对其个人均值的时点内变化；",
      "重新进入模型的个人均值成分表示被试间情境效应。"
    ),
    CGM_observation_level = "Level-1 预测变量以全部观测的总均值为参照，未分离时点内与被试间效应。",
    "预测变量未中心化，截距对应原始零点，且未分离时点内与被试间效应。"
  )
  if (!is.null(temporal$moderatorProtocol)) {
    interpretation <- paste0(
      interpretation,
      " Level-2 调节变量按被试等权进行总均值中心化。"
    )
  }
  list(
    level1Predictor = centered$protocol,
    level2Moderator = temporal$moderatorProtocol,
    crossLevelInteractions = as.list(temporal$interactionFormulas),
    time = temporal$timeProtocol,
    interpretation = interpretation
  )
}
