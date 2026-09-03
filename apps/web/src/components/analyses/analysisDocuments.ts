import type { DatasetVersion, MeasurementVersion } from '../../types'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import { methodDefinitions } from '../../methods/methodDefinitions'
import { expandMethodForLibrary } from '../../methods/methodLibraryPresets'
import { empiricalProcedures } from '../empirical/empiricalProcedures'
import { readEmpiricalHistory } from '../empirical/empiricalRunHistory'

export interface AnalysisDocumentIndexEntry {
  id: string
  projectId: string
  title: string
  methodId: string
  categoryId: string
  createdAt: string
  updatedAt: string
  pinned: boolean
  currentDraftId: string
  latestRunId?: string
  primaryRunId?: string
  archived?: boolean
  source: 'empirical'
  datasetVersionId: string
  measurementVersionId: string | null
  procedure: EmpiricalProcedure
}

export interface AnalysisRunIndexEntry {
  id: string
  analysisId: string
  draftRevision: number
  submittedSpec: null
  datasetVersionId: string
  measurementVersionId: string | null
  runStatus: 'legacy_indexed'
  freshness: 'current'
  resultId?: string
  warningCodes: string[]
  createdAt: string
}

export interface AnalysisDocumentIndex {
  schemaVersion: '1.0.0'
  migrationVersion: 1
  documents: AnalysisDocumentIndexEntry[]
  runs: AnalysisRunIndexEntry[]
}

const INDEX_PREFIX = 'researchpath.analysis.index.v1'
const MAX_DOCUMENTS = 500
const MAX_RUNS = 3000
const expandedMethods = methodDefinitions.flatMap(expandMethodForLibrary)

function emptyIndex(): AnalysisDocumentIndex {
  return { schemaVersion: '1.0.0', migrationVersion: 1, documents: [], runs: [] }
}

function stableHash(value: string): string {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index)
    hash = Math.imul(hash, 16777619)
  }
  return (hash >>> 0).toString(16).padStart(8, '0')
}

function indexKey(projectId: string): string {
  return `${INDEX_PREFIX}:${projectId}`
}

function measurementIdentity(measurement: MeasurementVersion | null): string {
  return measurement?.id ?? 'raw'
}

function analysisIdentity(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  procedure: EmpiricalProcedure,
): string {
  return `${dataset.projectId}:${dataset.id}:${measurementIdentity(measurement)}:${procedure}`
}

function methodIdentity(procedure: EmpiricalProcedure) {
  const expanded = expandedMethods.find((method) => method.procedure === procedure)
  if (expanded) return { methodId: expanded.id, title: expanded.label, categoryId: expanded.categoryId }

  const procedureDefinition = empiricalProcedures.find((definition) => definition.id === procedure)
  const exact = procedureDefinition
    ? methodDefinitions.find((method) => method.capabilitySliceIds.includes(procedureDefinition.slice))
    : undefined
  if (exact) return { methodId: exact.id, title: exact.label, categoryId: exact.categoryId }

  return {
    methodId: `empirical.${procedure}`,
    title: procedureDefinition?.label ?? procedure,
    categoryId: procedure === 'longitudinal' ? 'longitudinal' : procedure === 'diary' ? 'diary' : 'descriptives-relations',
  }
}

function isStoredIndex(value: unknown): value is AnalysisDocumentIndex {
  if (!value || typeof value !== 'object') return false
  const index = value as Partial<AnalysisDocumentIndex>
  return index.schemaVersion === '1.0.0'
    && index.migrationVersion === 1
    && Array.isArray(index.documents)
    && Array.isArray(index.runs)
    && index.documents.length <= MAX_DOCUMENTS
    && index.runs.length <= MAX_RUNS
}

function readIndex(projectId: string): AnalysisDocumentIndex {
  try {
    const raw = localStorage.getItem(indexKey(projectId))
    if (!raw || raw.length > 2_000_000) return emptyIndex()
    const value: unknown = JSON.parse(raw)
    return isStoredIndex(value) ? value : emptyIndex()
  } catch {
    return emptyIndex()
  }
}

function saveIndex(projectId: string, index: AnalysisDocumentIndex) {
  try {
    localStorage.setItem(indexKey(projectId), JSON.stringify({
      ...index,
      documents: index.documents.slice(0, MAX_DOCUMENTS),
      runs: index.runs.slice(0, MAX_RUNS),
    }))
  } catch {
    // Existing server jobs and legacy run history remain the recovery source.
  }
}

function legacyHistoryKey(dataset: DatasetVersion, measurement: MeasurementVersion | null): string {
  return `researchpath.empirical.runs.v1:${dataset.id}:${measurement?.version ?? null}`
}

function ensureDocument(
  index: AnalysisDocumentIndex,
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  procedure: EmpiricalProcedure,
  createdAt: string,
): AnalysisDocumentIndexEntry {
  const id = `analysis_${stableHash(analysisIdentity(dataset, measurement, procedure))}`
  const existing = index.documents.find((document) => document.id === id)
  if (existing) return existing

  const method = methodIdentity(procedure)
  const document: AnalysisDocumentIndexEntry = {
    id,
    projectId: dataset.projectId,
    title: method.title,
    methodId: method.methodId,
    categoryId: method.categoryId,
    createdAt,
    updatedAt: createdAt,
    pinned: false,
    currentDraftId: `draft_${stableHash(`${id}:current`)}`,
    source: 'empirical',
    datasetVersionId: dataset.id,
    measurementVersionId: measurement?.id ?? null,
    procedure,
  }
  index.documents.unshift(document)
  return document
}

export function loadEmpiricalAnalysisIndex(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
): AnalysisDocumentIndex {
  const index = readIndex(dataset.projectId)
  const history = readEmpiricalHistory(legacyHistoryKey(dataset, measurement))
  let changed = false

  history.forEach((entry) => {
    const document = ensureDocument(index, dataset, measurement, entry.procedure, entry.createdAt)
    if (!index.runs.some((run) => run.id === entry.id)) {
      index.runs.unshift({
        id: entry.id,
        analysisId: document.id,
        draftRevision: 0,
        submittedSpec: null,
        datasetVersionId: dataset.id,
        measurementVersionId: measurement?.id ?? null,
        runStatus: 'legacy_indexed',
        freshness: 'current',
        warningCodes: [],
        createdAt: entry.createdAt,
      })
      changed = true
    }
    if (!document.latestRunId || entry.createdAt >= document.updatedAt) {
      document.latestRunId = entry.id
      document.updatedAt = entry.createdAt
      changed = true
    }
  })

  if (changed) saveIndex(dataset.projectId, index)
  return index
}

export function analysisDocumentsForDataset(
  index: AnalysisDocumentIndex,
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
): AnalysisDocumentIndexEntry[] {
  const measurementVersionId = measurement?.id ?? null
  return index.documents
    .filter((document) => !document.archived
      && document.datasetVersionId === dataset.id
      && document.measurementVersionId === measurementVersionId)
    .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt.localeCompare(a.updatedAt))
}

export function analysisRunsForDocument(
  index: AnalysisDocumentIndex,
  analysisId: string,
): AnalysisRunIndexEntry[] {
  return index.runs
    .filter((run) => run.analysisId === analysisId)
    .sort((a, b) => b.createdAt.localeCompare(a.createdAt))
}
