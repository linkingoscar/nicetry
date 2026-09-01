import type { DataQualityRun, DatasetVariable } from '../types'

export function metric(run: DataQualityRun | undefined, name: string): Record<string, unknown> {
  const value = run?.metrics?.[name]
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

export function metricNumber(run: DataQualityRun | undefined, name: string, key: string): number | null {
  const value = metric(run, name)[key]
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

export function parseExpectedValue(value: string): string | number | boolean {
  if (value === 'true') return true
  if (value === 'false') return false
  const number = Number(value)
  return value.trim() !== '' && Number.isFinite(number) ? number : value
}

export function variableLabel(variable: DatasetVariable): string {
  return `${variable.label} (${variable.originalName})`
}
