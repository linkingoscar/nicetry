export function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

export function formatCI(lower?: number | null, upper?: number | null): string {
  return lower === null || lower === undefined || upper === null || upper === undefined
    ? '—'
    : `[${lower.toFixed(3)}, ${upper.toFixed(3)}]`
}

export function confidenceLabel(confidenceLevel?: number | null): string {
  return typeof confidenceLevel === 'number' && confidenceLevel > 0 && confidenceLevel < 1
    ? `${Math.round(confidenceLevel * 100)}% CI`
    : 'CI'
}

export function invarianceApaSection(apaTables: string | undefined) {
  if (!apaTables) return ''
  const start = apaTables.indexOf('### 表：多群组测量等值性检验')
  if (start < 0) return ''
  const nextHeading = apaTables.indexOf('\n### 表：', start + 5)
  return apaTables.slice(start, nextHeading < 0 ? undefined : nextHeading).trim()
}
