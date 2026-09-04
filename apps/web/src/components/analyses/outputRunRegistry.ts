import { registerServerAnalysisRun } from '../../api/analysis-index'
import type { DatasetVersion, MeasurementVersion } from '../../types'

export type RegisteredOutputSource = 'model' | 'advanced'
export type RegisteredOutputFreshness = 'current' | 'stale'

export interface RegisteredOutputRun {
  runId: string
  analysisId?: string
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

function stableHash(value: string): string {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

export function registeredOutputAnalysisId(entry: RegisteredOutputRun): string {
  if (entry.analysisId && ID_PATTERN.test(entry.analysisId)) return entry.analysisId
  if (entry.modelId && ID_PATTERN.test(entry.modelId)) {
    return `analysis_${stableHash(`${entry.source}:${entry.modelId}:${entry.datasetVersionId}`)}`
  }
  return `analysis_${stableHash(`${entry.source}:${entry.runId}`)}`
}

function isEntry(value: unknown, projectId: string): value is RegisteredOutputRun {
  if (!value || typeof value !== 'object') return false
  const entry = value as Partial<RegisteredOutputRun>
  return entry.projectId === projectId
    && typeof entry.runId === 'string'
    && ID_PATTERN.test(entry.runId)
    && (entry.analysisId === undefined || (typeof entry.analysisId === 'string' && ID_PATTERN.test(entry.analysisId)))
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
      .map((entry) => ({ ...entry, analysisId: registeredOutputAnalysisId(entry) }))
      .slice(0, MAX_RUNS)
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
  } catch {
    return []
  }
}

export function registerOutputRun(entry: RegisteredOutputRun): RegisteredOutputRun[] {
  const normalized: RegisteredOutputRun = {
    ...entry,
    analysisId: registeredOutputAnalysisId(entry),
    label: entry.label.trim().slice(0, 200) || entry.methodId,
  }
  if (!isEntry(normalized, normalized.projectId)) return readRegisteredOutputRuns(entry.projectId)

  const current = readRegisteredOutputRuns(normalized.projectId)
  const next = [normalized, ...current.filter((run) => run.runId !== normalized.runId)].slice(0, MAX_RUNS)
  try {
    localStorage.setItem(storageKey(normalized.projectId), JSON.stringify(next))
  } catch {
    // The server job and server AnalysisIndex remain authoritative when browser persistence is unavailable.
  }
  void registerServerAnalysisRun(normalized.projectId, {
    runId: normalized.runId,
    analysisId: normalized.analysisId ?? registeredOutputAnalysisId(normalized),
    source: normalized.source,
    methodId: normalized.methodId,
    label: normalized.label,
    family: normalized.family,
    modelId: normalized.modelId,
    datasetVersionId: normalized.datasetVersionId,
    measurementVersionId: normalized.measurementVersionId,
    createdAt: normalized.createdAt,
  }).catch(() => {
    // GET /analysis-index can still reconstruct the reference from persisted server job state.
  })
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
