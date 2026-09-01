import type {
  AnalysisContextQuery,
  AnalysisDraft,
  AnalysisDraftCreateRequest,
  AnalysisDraftMutation,
  ApplicableCapabilitiesResponse,
  ResolvedAnalysisContext,
} from '../types/analysis-context'
import { requestJson } from './client'

function queryString(query: Omit<AnalysisContextQuery, 'datasetId'>): string {
  const params = new URLSearchParams()
  if (query.measurementVersion !== null && query.measurementVersion !== undefined) {
    params.set('measurementVersion', String(query.measurementVersion))
  }
  if (query.sampleVersionId) params.set('sampleVersionId', query.sampleVersionId)
  if (query.imputationVersionId) params.set('imputationVersionId', query.imputationVersionId)
  const encoded = params.toString()
  return encoded ? `?${encoded}` : ''
}

export function getResolvedAnalysisContext(
  { datasetId, ...query }: AnalysisContextQuery,
  signal?: AbortSignal,
): Promise<ResolvedAnalysisContext> {
  return requestJson(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/resolved-analysis-context${queryString(query)}`,
    signal ? { signal } : undefined,
  )
}

export function getApplicableCapabilities(
  datasetId: string,
  contextHash: string,
  signal?: AbortSignal,
): Promise<ApplicableCapabilitiesResponse> {
  return requestJson(
    `/api/v1/datasets/${encodeURIComponent(datasetId)}/applicable-capabilities?contextHash=${encodeURIComponent(contextHash)}`,
    signal ? { signal } : undefined,
  )
}

export function createAnalysisDraft(datasetId: string, request: AnalysisDraftCreateRequest): Promise<AnalysisDraft> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/analysis-drafts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export function getAnalysisDraft(draftId: string): Promise<AnalysisDraft> {
  return requestJson(`/api/v1/analysis-drafts/${encodeURIComponent(draftId)}`)
}

export function getAnalysisDraftValidity(draftId: string): Promise<AnalysisDraft> {
  return requestJson(`/api/v1/analysis-drafts/${encodeURIComponent(draftId)}/validity`)
}

export function updateAnalysisDraft(draftId: string, request: AnalysisDraftMutation): Promise<AnalysisDraft> {
  return requestJson(`/api/v1/analysis-drafts/${encodeURIComponent(draftId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}
