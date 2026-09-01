import type { AnalysisJob, ResultBundle } from '../types'
import type { StudyPlanBinding } from '../types/workflows'
import { requestJson } from './client'

export function runFrozenModel(
  datasetId: string,
  modelId: string,
  version: number,
  studyPlanBinding?: StudyPlanBinding,
): Promise<AnalysisJob> {
  const init: RequestInit = { method: 'POST' }
  if (studyPlanBinding) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify({ studyPlanBinding })
  }
  return requestJson<AnalysisJob>(
    `/api/v1/datasets/${datasetId}/models/${modelId}/versions/${version}/analysis`,
    init,
  )
}

export function getAnalysisJob(runId: string): Promise<AnalysisJob> {
  return requestJson<AnalysisJob>(`/api/v1/analyses/${runId}`)
}

export function cancelAnalysisJob(runId: string): Promise<AnalysisJob> {
  return requestJson<AnalysisJob>(`/api/v1/analyses/${runId}`, { method: 'DELETE' })
}

export function analysisExportUrl(runId: string, includeData: boolean): string {
  return `/api/v1/analyses/${runId}/export?include_data=${includeData}`
}

export function getAnalysisResult(runId: string): Promise<ResultBundle> {
  return requestJson<ResultBundle>(`/api/v1/analyses/${runId}/result`)
}
