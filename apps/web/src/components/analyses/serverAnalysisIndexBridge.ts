import type { ServerAnalysisDocument, ServerAnalysisIndex } from '../../api/analysis-index'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import type {
  AnalysisDocumentIndex,
  AnalysisDocumentIndexEntry,
  AnalysisRunIndexEntry,
} from './analysisDocuments'
import type { RegisteredOutputRun } from './outputRunRegistry'

const EMPIRICAL_PROCEDURES = new Set<EmpiricalProcedure>([
  'descriptives',
  'frequencies',
  'missing',
  'correlation',
  'reliability',
  'efa',
  'cfa',
  'validity',
  'common_method',
  'invariance',
  'groups',
  'aggregation',
  'regression',
  'relative_importance',
  'response_surface',
  'longitudinal',
  'diary',
])

function isEmpiricalProcedure(value: unknown): value is EmpiricalProcedure {
  return typeof value === 'string' && EMPIRICAL_PROCEDURES.has(value as EmpiricalProcedure)
}

export function serverDocumentFromEmpirical(
  document: AnalysisDocumentIndexEntry,
): ServerAnalysisDocument {
  return {
    id: document.id,
    projectId: document.projectId,
    title: document.title,
    methodId: document.methodId,
    categoryId: document.categoryId,
    source: 'empirical',
    datasetVersionId: document.datasetVersionId,
    measurementVersionId: document.measurementVersionId,
    procedure: document.procedure,
    createdAt: document.createdAt,
    updatedAt: document.updatedAt,
    currentDraftId: document.currentDraftId,
    latestRunId: document.latestRunId,
    primaryRunId: document.primaryRunId,
    pinned: document.pinned,
    archived: document.archived,
  }
}

export function mergeEmpiricalServerIndex(
  local: AnalysisDocumentIndex,
  server?: ServerAnalysisIndex,
): AnalysisDocumentIndex {
  if (!server) return local
  const documents = new Map(local.documents.map((document) => [document.id, document]))
  server.documents.forEach((document) => {
    if (document.source !== 'empirical' || !isEmpiricalProcedure(document.procedure)) return
    const existing = documents.get(document.id)
    const localIsNewer = Boolean(existing && existing.updatedAt >= document.updatedAt)
    documents.set(document.id, {
      id: document.id,
      projectId: document.projectId,
      title: localIsNewer && existing ? existing.title : document.title,
      methodId: document.methodId,
      categoryId: document.categoryId,
      createdAt: existing?.createdAt ?? document.createdAt,
      updatedAt: localIsNewer && existing ? existing.updatedAt : document.updatedAt,
      pinned: localIsNewer && existing ? existing.pinned : document.pinned,
      currentDraftId: document.currentDraftId ?? existing?.currentDraftId ?? `draft_${document.id}`,
      latestRunId: document.latestRunId ?? existing?.latestRunId,
      primaryRunId: localIsNewer && existing ? existing.primaryRunId : document.primaryRunId,
      archived: localIsNewer && existing ? existing.archived : document.archived,
      source: 'empirical',
      datasetVersionId: document.datasetVersionId,
      measurementVersionId: document.measurementVersionId,
      procedure: document.procedure,
    })
  })

  const runs = new Map(local.runs.map((run) => [run.id, run]))
  server.runs.forEach((run) => {
    if (run.source !== 'empirical' || !documents.has(run.analysisId)) return
    const existing = runs.get(run.id)
    const next: AnalysisRunIndexEntry = {
      id: run.id,
      analysisId: run.analysisId,
      draftRevision: existing?.draftRevision ?? 0,
      submittedSpec: null,
      datasetVersionId: run.datasetVersionId,
      measurementVersionId: run.measurementVersionId,
      runStatus: 'legacy_indexed',
      freshness: existing?.freshness ?? 'current',
      resultId: run.reportId ?? run.resultId ?? existing?.resultId,
      warningCodes: existing?.warningCodes ?? [],
      createdAt: run.createdAt,
    }
    runs.set(run.id, next)
  })

  return {
    ...local,
    documents: [...documents.values()],
    runs: [...runs.values()],
  }
}

export function mergeRegisteredServerRuns(
  local: RegisteredOutputRun[],
  server?: ServerAnalysisIndex,
): RegisteredOutputRun[] {
  if (!server) return local
  const runs = new Map(local.map((run) => [`${run.source}:${run.runId}`, run]))
  server.runs.forEach((run) => {
    if (run.source !== 'model' && run.source !== 'advanced') return
    const source = run.source
    const key = `${source}:${run.id}`
    const existing = runs.get(key)
    runs.set(key, {
      runId: run.id,
      analysisId: run.analysisId,
      projectId: run.projectId,
      datasetVersionId: run.datasetVersionId,
      measurementVersionId: run.measurementVersionId,
      source,
      label: existing?.label ?? run.label,
      methodId: existing?.methodId ?? run.methodId,
      family: existing?.family ?? run.family,
      modelId: existing?.modelId ?? run.modelId,
      createdAt: existing?.createdAt ?? run.createdAt,
    })
  })
  return [...runs.values()].sort((a, b) => b.createdAt.localeCompare(a.createdAt))
}
