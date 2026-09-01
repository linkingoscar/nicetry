export function formatMetric(value: number | null | undefined, digits = 3): string {
  return value == null ? '—' : value.toFixed(digits);
}

export function formatPValue(value: number | null | undefined): string {
  if (value == null) return '—';
  return value < 0.001 ? '< .001' : value.toFixed(3).replace(/^0/, '');
}

export function formatCI(lower: number | null | undefined, upper: number | null | undefined, digits = 3): string {
  if (lower == null || upper == null) return '—';
  return `[${lower.toFixed(digits)}, ${upper.toFixed(digits)}]`;
}
