import type { EmpiricalProcedure } from '../types/empirical-types'
import { requestJson } from './client'
import type { EmpiricalDraft } from '../components/empirical/empiricalDrafts'

export type ServerAnalysisSource = 'empirical' | 'model' | 'advanced'

export interface ServerAnalysisDocument {
  id: string
  projectId: string
  title: string
  methodId: string
  categoryId: string
  source: ServerAnalysisSource
  datasetVersionId: string
  measurementVersionId: string | null
  procedure?: EmpiricalProcedure
  createdAt: string
  updatedAt: string
  currentDraftId?: string
  latestRunId?: string
  primaryRunId?: string
  pinned: boolean
  archived?: boolean
}

export interface ServerAnalysisRun {
  id: string
  analysisId: string
  projectId: string
  source: ServerAnalysisSource
  methodId: string
  label: string
  family?: string
  modelId?: string
  datasetVersionId: string
  measurementVersionId: string | null
  status: string
  resultId?: string
  reportId?: string
  createdAt: string
}

export interface ServerAnalysisIndex {
  schemaVersion: '1.0.0'
  projectId: string
  documents: ServerAnalysisDocument[]
  runs: ServerAnalysisRun[]
  rebuiltFromServerJobs: boolean
}

export interface ServerEmpiricalDraft {
  schemaVersion: '1.0.0'
  projectId: string
  analysisId: string
  revision: number
  createdAt: string
  updatedAt: string
  payload: EmpiricalDraft
}

export interface RegisterServerAnalysisRunInput {
  id?: string
  runId?: string
  analysisId: string
  source: ServerAnalysisSource
  methodId: string
  label: string
  categoryId?: string
  family?: string
  modelId?: string
  procedure?: EmpiricalProcedure
  datasetVersionId: string
  measurementVersionId: string | null
  status?: string
  resultId?: string
  reportId?: string
  createdAt: string
}

export function getServerAnalysisIndex(projectId: string): Promise<ServerAnalysisIndex> {
  return requestJson(`/api/v1/projects/${encodeURIComponent(projectId)}/analysis-index`)
}

export function upsertServerAnalysisDocument(
  document: ServerAnalysisDocument,
): Promise<ServerAnalysisDocument> {
  return requestJson(
    `/api/v1/projects/${encodeURIComponent(document.projectId)}/analysis-documents/${encodeURIComponent(document.id)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(document),
    },
  )
}

export function patchServerAnalysisDocument(
  projectId: string,
  analysisId: string,
  patch: { title?: string; pinned?: boolean; archived?: boolean; primaryRunId?: string | null },
): Promise<ServerAnalysisDocument> {
  return requestJson(
    `/api/v1/projects/${encodeURIComponent(projectId)}/analysis-documents/${encodeURIComponent(analysisId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    },
  )
}

export function registerServerAnalysisRun(
  projectId: string,
  run: RegisterServerAnalysisRunInput,
): Promise<ServerAnalysisRun> {
  return requestJson(`/api/v1/projects/${encodeURIComponent(projectId)}/analysis-runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(run),
  })
}

export function getServerEmpiricalDraft(projectId: string, analysisId: string): Promise<ServerEmpiricalDraft | null> {
  return requestJson(
    `/api/v1/projects/${encodeURIComponent(projectId)}/analysis-documents/${encodeURIComponent(analysisId)}/draft`,
  )
}

export function saveServerEmpiricalDraft(
  projectId: string,
  analysisId: string,
  payload: EmpiricalDraft,
  expectedRevision: number,
): Promise<ServerEmpiricalDraft> {
  return requestJson(
    `/api/v1/projects/${encodeURIComponent(projectId)}/analysis-documents/${encodeURIComponent(analysisId)}/draft`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expectedRevision, payload }),
    },
  )
}
