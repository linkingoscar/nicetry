import type {
  ImputationCompatibilityResponse,
  ImputationPlanCreateRequest,
  ImputationPlanVersion,
} from '../types/workflows'
import type { AdvancedJobResponse } from '../types/advanced'
import { requestJson } from './client'

export function createImputationPlan(
  datasetId: string,
  request: ImputationPlanCreateRequest,
): Promise<ImputationPlanVersion> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/imputation-plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export function getImputationPlan(planId: string): Promise<ImputationPlanVersion> {
  return requestJson(`/api/v1/imputation-plans/${encodeURIComponent(planId)}`)
}

export function runImputationPlan(planId: string): Promise<{
  planVersionId: string
  imputationPlanVersionId: string
  imputationDatasetVersionId: string
  contextHash: string
  job: AdvancedJobResponse
}> {
  return requestJson(`/api/v1/imputation-plans/${encodeURIComponent(planId)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
}

export function getImputationPlanCompatibility(
  planId: string,
  draftId: string,
): Promise<ImputationCompatibilityResponse> {
  return requestJson(
    `/api/v1/imputation-plans/${encodeURIComponent(planId)}/compatible-analyses?draftId=${encodeURIComponent(draftId)}`,
  )
}

export function getImputationDatasetCompatibility(
  imputationDatasetId: string,
  draftId: string,
): Promise<ImputationCompatibilityResponse> {
  return requestJson(
    `/api/v1/imputation-datasets/${encodeURIComponent(imputationDatasetId)}/compatibility?draftId=${encodeURIComponent(draftId)}`,
  )
}
