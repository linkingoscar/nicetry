dsem_split_chains <- function(chains) {
  original_draw_count <- ncol(chains)
  half <- floor(original_draw_count / 2)
  if (half >= 2L) {
    return(rbind(
      chains[, seq_len(half), drop = FALSE],
      chains[, (original_draw_count - half + 1L):original_draw_count, drop = FALSE]
    ))
  }
  chains
}

dsem_basic_rhat <- function(chains) {
  chain_count <- nrow(chains)
  draw_count <- ncol(chains)
  if (chain_count < 2L || draw_count < 2L) return(NA_real_)
  chain_means <- rowMeans(chains)
  within <- mean(apply(chains, 1L, var))
  between <- draw_count * var(chain_means)
  if (!is.finite(within) || within <= 0) return(NA_real_)
  sqrt(((draw_count - 1) / draw_count * within + between / draw_count) / within)
}

dsem_rank_normalize <- function(chains) {
  ranked <- rank(as.numeric(chains), ties.method = "average")
  normalized <- qnorm((ranked - 3 / 8) / (length(ranked) + 1 / 4))
  matrix(normalized, nrow = nrow(chains), ncol = ncol(chains))
}

dsem_rhat <- function(chains) {
  split <- dsem_split_chains(chains)
  rank_rhat <- dsem_basic_rhat(dsem_rank_normalize(split))
  folded <- abs(split - median(as.numeric(split)))
  folded_rhat <- dsem_basic_rhat(dsem_rank_normalize(folded))
  max(c(rank_rhat, folded_rhat), na.rm = TRUE)
}

dsem_ess_core <- function(chains) {
  chain_count <- nrow(chains)
  draw_count <- ncol(chains)
  max_lag <- min(100L, draw_count - 1L)
  if (max_lag < 2L) return(NA_real_)
  autocorrelations <- vapply(seq_len(max_lag), function(lag) {
    mean(vapply(seq_len(chain_count), function(chain) {
      values <- chains[chain, ]
      correlation <- suppressWarnings(cor(
        values[seq_len(draw_count - lag)],
        values[(lag + 1L):draw_count]
      ))
      if (is.finite(correlation)) correlation else 0
    }, numeric(1)))
  }, numeric(1))
  positive_sum <- 0
  for (index in seq(1L, length(autocorrelations) - 1L, by = 2L)) {
    pair_sum <- autocorrelations[[index]] + autocorrelations[[index + 1L]]
    if (!is.finite(pair_sum) || pair_sum < 0) break
    positive_sum <- positive_sum + pair_sum
  }
  chain_count * draw_count / max(1, 1 + 2 * positive_sum)
}

dsem_modern_ess <- function(chains) {
  split <- dsem_split_chains(chains)
  normalized <- dsem_rank_normalize(split)
  bulk <- dsem_ess_core(normalized)
  values <- as.numeric(split)
  lower <- unname(quantile(values, 0.05))
  upper <- unname(quantile(values, 0.95))
  lower_indicator <- matrix(
    as.numeric(split <= lower),
    nrow = nrow(split),
    ncol = ncol(split)
  )
  upper_indicator <- matrix(
    as.numeric(split >= upper),
    nrow = nrow(split),
    ncol = ncol(split)
  )
  tail <- min(
    dsem_ess_core(lower_indicator),
    dsem_ess_core(upper_indicator),
    na.rm = TRUE
  )
  list(bulk = bulk, tail = tail)
}

dsem_summary_row <- function(chains, id, label, confidence_level) {
  values <- as.numeric(chains)
  alpha <- 1 - confidence_level
  ess <- dsem_modern_ess(chains)
  list(
    id = id,
    label = label,
    estimate = ensure_finite(mean(values)),
    posteriorSd = ensure_finite(sd(values)),
    lower = ensure_finite(unname(quantile(values, alpha / 2))),
    upper = ensure_finite(unname(quantile(values, 1 - alpha / 2))),
    probabilityPositive = ensure_finite(mean(values > 0)),
    rHat = ensure_finite(dsem_rhat(chains)),
    effectiveSampleSize = ensure_finite(min(ess$bulk, ess$tail)),
    bulkEffectiveSampleSize = ensure_finite(ess$bulk),
    tailEffectiveSampleSize = ensure_finite(ess$tail),
    mcseMean = ensure_finite(sd(values) / sqrt(ess$bulk))
  )
}
