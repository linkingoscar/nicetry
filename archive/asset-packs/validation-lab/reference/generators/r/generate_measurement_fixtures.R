args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("usage: generate_measurement_fixtures.R <output-dir>")
output_dir <- args[[1]]
dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)

set.seed(20260722)
n <- 600L
group <- rep(c("g1", "g2"), each = n / 2L)
z1 <- stats::rnorm(n)
z2 <- stats::rnorm(n)
factor_x <- z1 + ifelse(group == "g2", 0.25, 0)
factor_y <- 0.35 * z1 + sqrt(1 - 0.35^2) * z2
make_item <- function(factor, loading) loading * factor + sqrt(1 - loading^2) * stats::rnorm(n)
continuous <- data.frame(
  subject_id = seq_len(n),
  group = group,
  marker = stats::rnorm(n),
  x1 = make_item(factor_x, 0.82),
  x2 = make_item(factor_x, 0.78),
  x3 = make_item(factor_x, 0.75),
  y1 = make_item(factor_y, 0.84),
  y2 = make_item(factor_y, 0.80),
  y3 = make_item(factor_y, 0.77)
)
utils::write.csv(continuous, file.path(output_dir, "measurement-continuous.csv"),
  row.names = FALSE, fileEncoding = "UTF-8")

ordinal <- continuous
for (name in c("x1", "x2", "x3", "y1", "y2", "y3")) {
  ordinal[[name]] <- as.integer(cut(ordinal[[name]],
    breaks = c(-Inf, -1, -0.3, 0.3, 1, Inf), labels = FALSE))
}
utils::write.csv(ordinal, file.path(output_dir, "measurement-ordinal.csv"),
  row.names = FALSE, fileEncoding = "UTF-8")

general <- stats::rnorm(n); specific_1 <- stats::rnorm(n); specific_2 <- stats::rnorm(n)
bifactor <- data.frame(subject_id = seq_len(n))
for (index in seq_len(3L)) {
  bifactor[[paste0("y", index)]] <- 0.72 * general + 0.38 * specific_1 +
    sqrt(1 - 0.72^2 - 0.38^2) * stats::rnorm(n)
}
for (index in 4:6) {
  bifactor[[paste0("y", index)]] <- 0.75 * general + 0.32 * specific_2 +
    sqrt(1 - 0.75^2 - 0.32^2) * stats::rnorm(n)
}
utils::write.csv(bifactor, file.path(output_dir, "bifactor-continuous.csv"),
  row.names = FALSE, fileEncoding = "UTF-8")

theta <- stats::rnorm(n)
irt_group <- rep(c(0L, 1L), each = n / 2L)
discrimination <- c(1.4, 1.2, 1.8, 1.1)
difficulty <- c(-0.25, 0.1, -0.8, 0.45)
irt <- data.frame(subject_id = seq_len(n), group = irt_group)
for (index in seq_along(discrimination)) {
  linear <- discrimination[[index]] * (theta - difficulty[[index]])
  if (index == 2L) linear <- linear + 0.65 * irt_group
  irt[[paste0("i", index)]] <- stats::rbinom(n, 1L, stats::plogis(linear))
}
utils::write.csv(irt, file.path(output_dir, "irt-dif.csv"),
  row.names = FALSE, fileEncoding = "UTF-8")
