import type {
  AdvancedAnalysisCapability,
  AdvancedAnalysisSpec,
  AdvancedAnalysisValidation,
  AdvancedJobResponse,
  AdvancedResultResponse
} from '../types'
import type { AdvancedAnalysisRequest } from './contracts'
import { requestJson } from './client'

export function getAdvancedAnalysisCapabilities(): Promise<{
  schemaVersion: string
  capabilities: AdvancedAnalysisCapability[]
}> {
  return requestJson('/api/v1/advanced-analyses/capabilities')
}

export function validateAdvancedAnalysisSpec(
  spec: AdvancedAnalysisSpec,
  datasetId?: string,
): Promise<AdvancedAnalysisValidation> {
  const body = { datasetId: datasetId ?? null, spec } satisfies AdvancedAnalysisRequest
  return requestJson('/api/v1/advanced-analyses/validate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

/** Call only when the capability catalog reports executionAvailable=true. */
export function runAdvancedAnalysis(
  spec: AdvancedAnalysisSpec,
  datasetId?: string,
): Promise<AdvancedJobResponse> {
  const body = { datasetId: datasetId ?? null, spec } satisfies AdvancedAnalysisRequest
  return requestJson('/api/v1/advanced-analyses', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getAdvancedAnalysisStatus(runId: string): Promise<AdvancedJobResponse> {
  return requestJson(`/api/v1/advanced-analyses/${runId}`)
}

export function getAdvancedAnalysisResult(runId: string): Promise<AdvancedResultResponse> {
  return requestJson(`/api/v1/advanced-analyses/${runId}/result`)
}

export function advancedAnalysisExportUrl(runId: string, includeData = false): string {
  const suffix = includeData ? '?include_data=true' : ''
  return `/api/v1/advanced-analyses/${encodeURIComponent(runId)}/export${suffix}`
}

export function cancelAdvancedAnalysis(runId: string): Promise<AdvancedJobResponse> {
  return requestJson(`/api/v1/advanced-analyses/${runId}`, {
    method: 'DELETE',
  })
}
