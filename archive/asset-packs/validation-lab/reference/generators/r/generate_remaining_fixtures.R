args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("usage: generate_remaining_fixtures.R <output-dir>")
output_dir <- args[[1]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

set.seed(20260723)

# Multiple imputation: correlated predictors with MAR missingness.
n <- 240L
x1 <- stats::rnorm(n)
x2 <- 0.55 * x1 + stats::rnorm(n, sd = 0.8)
interaction <- x1 * x2
x1[stats::runif(n) < stats::plogis(-2 + 0.4 * x2)] <- NA
x2[stats::runif(n) < stats::plogis(-2 - 0.3 * ifelse(is.na(x1), 0, x1))] <- NA
interaction[is.na(x1) | is.na(x2)] <- NA
utils::write.csv(data.frame(x1, x2, interaction), file.path(output_dir, "mice.csv"), row.names = FALSE)

# ESM: AR(1) resets at each person-day boundary.
phi <- 0.42; rows <- list(); index <- 1L
for (person in seq_len(45L)) {
  person_effect <- stats::rnorm(1L, sd = 0.9)
  for (day in seq_len(7L)) {
    errors <- numeric(6L); errors[[1]] <- stats::rnorm(1L, sd = 0.55 / sqrt(1 - phi^2))
    for (prompt in 2:6) errors[[prompt]] <- phi * errors[[prompt - 1L]] + stats::rnorm(1L, sd = 0.55)
    for (prompt in seq_len(6L)) {
      rows[[index]] <- data.frame(person_id = person, day = day, prompt = prompt,
        affect = 4 + person_effect + errors[[prompt]])
      index <- index + 1L
    }
  }
}
utils::write.csv(do.call(rbind, rows), file.path(output_dir, "esm.csv"), row.names = FALSE)

# Four-wave RI-CLPM with stable trait and within-person reciprocal dynamics.
n <- 700L
traits <- MASS::mvrnorm(n, mu = c(0, 0), Sigma = matrix(c(1.3, 0.55, 0.55, 1.6), 2L))
wx <- matrix(0, n, 4L); wy <- matrix(0, n, 4L)
wx[, 1] <- stats::rnorm(n, sd = 0.75); wy[, 1] <- stats::rnorm(n, sd = 0.8)
for (wave in 2:4) {
  wx[, wave] <- 0.42 * wx[, wave - 1L] + 0.14 * wy[, wave - 1L] + stats::rnorm(n, sd = 0.55)
  wy[, wave] <- 0.48 * wy[, wave - 1L] + 0.24 * wx[, wave - 1L] + stats::rnorm(n, sd = 0.55)
}
riclpm <- data.frame(subject_id = seq_len(n))
for (wave in seq_len(4L)) riclpm[[paste0("x", wave)]] <- 10 + traits[, 1] + wx[, wave]
for (wave in seq_len(4L)) riclpm[[paste0("y", wave)]] <- 15 + traits[, 2] + wy[, wave]
utils::write.csv(riclpm, file.path(output_dir, "riclpm.csv"), row.names = FALSE)

# Two-level mediation with distinct within- and between-cluster pathways.
rows <- list(); index <- 1L
for (cluster in seq_len(60L)) {
  xb <- stats::rnorm(1L); cluster_m <- stats::rnorm(1L, sd = 0.35); cluster_y <- stats::rnorm(1L, sd = 0.45)
  for (member in seq_len(12L)) {
    xw <- stats::rnorm(1L); x <- xb + xw
    m <- 0.75 * xb + 0.55 * xw + cluster_m + stats::rnorm(1L, sd = 0.55)
    y <- 0.25 * xb + 0.15 * xw + 0.85 * (0.75 * xb + cluster_m) +
      0.65 * (m - (0.75 * xb + cluster_m)) + cluster_y + stats::rnorm(1L, sd = 0.65)
    rows[[index]] <- data.frame(cluster_id = cluster, x = x, m = m, y = y); index <- index + 1L
  }
}
utils::write.csv(do.call(rbind, rows), file.path(output_dir, "mediation.csv"), row.names = FALSE)

# Clustered treatment data for CR2 small-sample correction.
rows <- list(); index <- 1L
for (cluster in seq_len(36L)) {
  random_intercept <- stats::rnorm(1L, sd = 1.1)
  for (member in seq_len(10L)) {
    treatment <- stats::rbinom(1L, 1L, 0.5)
    rows[[index]] <- data.frame(cluster_id = cluster, treatment = treatment,
      outcome = 10 + 2.4 * treatment + random_intercept + stats::rnorm(1L, sd = 1.2))
    index <- index + 1L
  }
}
utils::write.csv(do.call(rbind, rows), file.path(output_dir, "cr2.csv"), row.names = FALSE)

# Multiverse data: stable focal effect with correlated candidate controls and a few outliers.
n <- 260L
cov1 <- stats::rnorm(n); cov2 <- 0.35 * cov1 + stats::rnorm(n)
x <- 0.3 * cov1 - 0.2 * cov2 + stats::rnorm(n)
y <- 1.05 * x + 0.45 * cov1 - 0.25 * cov2 + stats::rt(n, df = 6L) * 0.65
y[c(7, 89, 201)] <- y[c(7, 89, 201)] + c(7, -8, 6)
utils::write.csv(data.frame(x, y, cov1, cov2), file.path(output_dir, "spec-curve.csv"), row.names = FALSE)
