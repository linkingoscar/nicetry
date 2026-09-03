import type {
  DatasetVersion,
  EmpiricalAnalysisJob,
  EmpiricalAnalysisOptions,
  MeasurementVersion,
} from '../../types'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import { loadEmpiricalAnalysisIndex } from './analysisDocuments'

export interface AnalysisRunDetail {
  runId: string
  analysisId: string
  procedure: EmpiricalProcedure
  draftRevision: number
  submittedSpec: EmpiricalAnalysisOptions
  runStatus: EmpiricalAnalysisJob['status']
  qualityStatus: 'clean' | 'warning'
  freshness: 'current'
  resultId: string | null
  warningCodes: string[]
  createdAt: string
  updatedAt: string
}

interface AnalysisRunDetailStore {
  schemaVersion: '1.0.0'
  details: AnalysisRunDetail[]
}

const STORE_PREFIX = 'researchpath.analysis.run-details.v1'
const MAX_DETAILS = 3000

function storeKey(projectId: string) {
  return `${STORE_PREFIX}:${projectId}`
}

function readStore(projectId: string): AnalysisRunDetailStore {
  try {
    const raw = localStorage.getItem(storeKey(projectId))
    if (!raw || raw.length > 4_000_000) return { schemaVersion: '1.0.0', details: [] }
    const value = JSON.parse(raw) as Partial<AnalysisRunDetailStore>
    if (value.schemaVersion !== '1.0.0' || !Array.isArray(value.details) || value.details.length > MAX_DETAILS) {
      return { schemaVersion: '1.0.0', details: [] }
    }
    return { schemaVersion: '1.0.0', details: value.details }
  } catch {
    return { schemaVersion: '1.0.0', details: [] }
  }
}

function saveStore(projectId: string, store: AnalysisRunDetailStore) {
  try {
    localStorage.setItem(storeKey(projectId), JSON.stringify({
      schemaVersion: '1.0.0',
      details: store.details.slice(0, MAX_DETAILS),
    }))
  } catch {
    // The server job and compatibility run index remain the recovery sources.
  }
}

function specFingerprint(spec: EmpiricalAnalysisOptions) {
  return JSON.stringify(spec)
}

function nextDraftRevision(details: AnalysisRunDetail[], analysisId: string, spec: EmpiricalAnalysisOptions) {
  const siblings = details.filter((detail) => detail.analysisId === analysisId)
  const fingerprint = specFingerprint(spec)
  const matching = siblings.find((detail) => specFingerprint(detail.submittedSpec) === fingerprint)
  if (matching) return matching.draftRevision
  return siblings.reduce((maximum, detail) => Math.max(maximum, detail.draftRevision), 0) + 1
}

export function readAnalysisRunDetails(projectId: string): AnalysisRunDetail[] {
  return readStore(projectId).details
}

export function syncEmpiricalAnalysisRunDetail(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  job: EmpiricalAnalysisJob,
): boolean {
  const procedure = job.options.procedure
  if (!procedure) return false

  const index = loadEmpiricalAnalysisIndex(dataset, measurement)
  const runReference = index.runs.find((run) => run.id === job.id)
  if (!runReference) return false

  const store = readStore(dataset.projectId)
  const existing = store.details.find((detail) => detail.runId === job.id)
  const detail: AnalysisRunDetail = {
    runId: job.id,
    analysisId: runReference.analysisId,
    procedure,
    draftRevision: existing?.draftRevision
      ?? nextDraftRevision(store.details, runReference.analysisId, job.options),
    submittedSpec: job.options,
    runStatus: job.status,
    qualityStatus: job.warnings.length ? 'warning' : 'clean',
    freshness: 'current',
    resultId: job.status === 'succeeded' ? job.reportId : existing?.resultId ?? null,
    warningCodes: job.warnings.map((warning) => warning.code),
    createdAt: job.createdAt,
    updatedAt: job.updatedAt,
  }

  store.details = [detail, ...store.details.filter((item) => item.runId !== job.id)]
  saveStore(dataset.projectId, store)
  return true
}
