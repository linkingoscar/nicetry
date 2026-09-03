import type { DatasetVersion, MeasurementVersion } from '../../types'

export type RegisteredOutputSource = 'model' | 'advanced'
export type RegisteredOutputFreshness = 'current' | 'stale'

export interface RegisteredOutputRun {
  runId: string
  projectId: string
  datasetVersionId: string
  measurementVersionId: string | null
  source: RegisteredOutputSource
  label: string
  methodId: string
  family?: string
  modelId?: string
  createdAt: string
}

const KEY_PREFIX = 'researchpath.output.runs.v1'
const MAX_RUNS = 1000
const ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/

function storageKey(projectId: string) {
  return `${KEY_PREFIX}:${projectId}`
}

function isEntry(value: unknown, projectId: string): value is RegisteredOutputRun {
  if (!value || typeof value !== 'object') return false
  const entry = value as Partial<RegisteredOutputRun>
  return entry.projectId === projectId
    && typeof entry.runId === 'string'
    && ID_PATTERN.test(entry.runId)
    && typeof entry.datasetVersionId === 'string'
    && entry.datasetVersionId.length > 0
    && (entry.measurementVersionId === null || typeof entry.measurementVersionId === 'string')
    && (entry.source === 'model' || entry.source === 'advanced')
    && typeof entry.label === 'string'
    && entry.label.length > 0
    && entry.label.length <= 200
    && typeof entry.methodId === 'string'
    && entry.methodId.length > 0
    && typeof entry.createdAt === 'string'
}

export function readRegisteredOutputRuns(projectId: string): RegisteredOutputRun[] {
  try {
    const raw = localStorage.getItem(storageKey(projectId))
    if (!raw || raw.length > 2_000_000) return []
    const value: unknown = JSON.parse(raw)
    if (!Array.isArray(value)) return []
    return value
      .filter((entry): entry is RegisteredOutputRun => isEntry(entry, projectId))
      .slice(0, MAX_RUNS)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  } catch {
    return []
  }
}

export function registerOutputRun(entry: RegisteredOutputRun): RegisteredOutputRun[] {
  const normalized: RegisteredOutputRun = {
    ...entry,
    label: entry.label.trim().slice(0, 200) || entry.methodId,
  }
  if (!isEntry(normalized, normalized.projectId)) return readRegisteredOutputRuns(entry.projectId)

  const current = readRegisteredOutputRuns(normalized.projectId)
  const next = [normalized, ...current.filter((run) => run.runId !== normalized.runId)].slice(0, MAX_RUNS)
  try {
    localStorage.setItem(storageKey(normalized.projectId), JSON.stringify(next))
  } catch {
    // The server job remains authoritative even when browser indexing is unavailable.
  }
  return next
}

export function registeredOutputFreshness(
  run: RegisteredOutputRun,
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
): RegisteredOutputFreshness {
  if (run.datasetVersionId !== dataset.id) return 'stale'
  const measurementBound = run.source === 'model'
    || (run.source === 'advanced' && run.family === 'questionnaire_measurement')
  if (measurementBound && run.measurementVersionId && run.measurementVersionId !== (measurement?.id ?? null)) return 'stale'
  return 'current'
}
