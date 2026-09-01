/**
 * ResearchPath APA 7th Edition Statistical Formatting Utilities
 *
 * APA 7th Guidelines:
 * 1. For statistics bounded by -1.0 and 1.0 (such as p, r, R², η²), omit the leading zero before the decimal point (e.g., .001, .45).
 * 2. Statistical symbols (p, r, N, F, t, z, CI, etc.) should be presented with proper formatting.
 */

/**
 * Format a statistic bounded by 1 (e.g., r, R², p, η²), omitting the leading zero when < 1.
 */
export function formatAPAStat(val: number | null | undefined, digits = 3): string {
  if (typeof val !== 'number' || Number.isNaN(val)) return '—'
  const formatted = val.toFixed(digits)
  if (Math.abs(val) < 1) {
    return formatted.replace(/^(-?)0\./, '$1.')
  }
  return formatted
}
/**
 * Format a p-value according to APA 7th:
 * - If p < .001, return "< .001"
 * - Otherwise return formatted decimal without leading zero (e.g. ".042")
 */
export function formatAPAPValue(p: number | null | undefined): string {
  if (typeof p !== 'number' || Number.isNaN(p)) return '—'
  if (p < 0.001) return '< .001'
  return formatAPAStat(p, 3)
}

/**
 * Return significance stars or '(ns)' based on p-value.
 */
export function formatAPASigStars(p: number | null | undefined): string {
  if (typeof p !== 'number' || Number.isNaN(p)) return ''
  if (p < 0.001) return '***'
  if (p < 0.01) return '**'
  if (p < 0.05) return '*'
  return ' (ns)'
}

/**
 * Format a 95% confidence interval range in APA 7th style: 95% CI [.123, .456]
 */
export function formatAPAConfidenceInterval(
  lower: number | null | undefined,
  upper: number | null | undefined,
  digits = 3,
  confidenceLevel = 0.95
): string {
  if (
    typeof lower !== 'number' ||
    typeof upper !== 'number' ||
    Number.isNaN(lower) ||
    Number.isNaN(upper)
  ) {
    return '—'
  }
  const pct = Math.round(confidenceLevel * 100)
  return `${pct}% CI [${formatAPAStat(lower, digits)}, ${formatAPAStat(upper, digits)}]`
}
