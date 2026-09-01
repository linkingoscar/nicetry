import type {
  FrozenModelVersion,
  ModelDraftVersion,
  ModelSpec,
  ModelValidation,
} from '../types'
import type { ModelDraftRequest, ModelFreezeRequest } from './contracts'
import { requestJson } from './client'

export function validateDatasetModel(
  datasetId: string,
  modelSpec: ModelSpec,
): Promise<ModelValidation> {
  const body = { model_spec: { ...modelSpec } } satisfies ModelDraftRequest
  return requestJson<ModelValidation>(`/api/v1/datasets/${datasetId}/models/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function saveModelDraft(
  datasetId: string,
  modelSpec: ModelSpec,
): Promise<ModelDraftVersion> {
  const body = { model_spec: { ...modelSpec } } satisfies ModelDraftRequest
  return requestJson<ModelDraftVersion>(
    `/api/v1/datasets/${datasetId}/models/${modelSpec.modelId}/draft`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
}

export async function getModelDraft(
  datasetId: string,
  modelId: string,
): Promise<ModelDraftVersion | null> {
  return requestJson<ModelDraftVersion | null>(
    `/api/v1/datasets/${datasetId}/models/${modelId}/draft`,
  )
}

export function freezeModel(
  datasetId: string,
  modelSpec: ModelSpec,
  overrideReason: string,
): Promise<FrozenModelVersion> {
  const body = {
    model_spec: { ...modelSpec },
    override_reason: overrideReason.trim() || null,
  } satisfies ModelFreezeRequest
  return requestJson<FrozenModelVersion>(
    `/api/v1/datasets/${datasetId}/models/${modelSpec.modelId}/freeze`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    },
  )
}
