export function metric(value: number | null | undefined, digits = 3): string {
  return value === null || value === undefined ? '—' : value.toFixed(digits)
}

export function probability(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return value < 0.001 ? '< .001' : value.toFixed(3).replace(/^0/, '')
}

export function significance(value: number | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (value < 0.001) return '***'
  if (value < 0.01) return '**'
  if (value < 0.05) return '*'
  return ''
}
