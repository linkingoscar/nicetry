import type {
  ConstructDraft,
  DatasetMergeResponse,
  DatasetVersion,
  MeasurementVersion,
  VariableType,
} from '../types'
import type {
  DictionaryUpdateRequest,
  MeasurementUpdateRequest,
} from './contracts'
import { requestJson } from './client'

const MAX_UPLOAD_BYTES = 50 * 1024 * 1024

export function importDataset(file: File, selectedSheet?: string): Promise<DatasetVersion> {
  if (file.size > MAX_UPLOAD_BYTES) {
    return Promise.reject(new Error('上传文件超过 50 MB 限制'))
  }
  const body = new FormData()
  body.append('file', file)
  const url = selectedSheet
    ? `/api/v1/datasets/import?selectedSheet=${encodeURIComponent(selectedSheet)}`
    : '/api/v1/datasets/import'
  return requestJson<DatasetVersion>(url, { method: 'POST', body })
}

export function confirmDictionary(
  datasetId: string,
  variables: Array<{ id: string; confirmedType: VariableType }>,
): Promise<DatasetVersion> {
  const body = {
    variables: variables.map((variable) => ({
      id: variable.id,
      confirmed_type: variable.confirmedType,
    })),
  } satisfies DictionaryUpdateRequest
  return requestJson<DatasetVersion>(`/api/v1/datasets/${datasetId}/dictionary`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function saveMeasurement(
  datasetId: string,
  constructs: ConstructDraft[],
  changeNote: string,
): Promise<MeasurementVersion> {
  const body = {
    constructs: constructs.map((construct) => ({
      id: construct.id,
      name: construct.name,
      item_ids: construct.itemIds,
      reverse_item_ids: construct.reverseItemIds,
      theoretical_minimum: construct.theoreticalMinimum,
      theoretical_maximum: construct.theoreticalMaximum,
      aggregation: construct.aggregation,
      minimum_valid_proportion: construct.minimumValidProportion,
    })),
    change_note: changeNote.trim() || null,
  } satisfies MeasurementUpdateRequest
  return requestJson<MeasurementVersion>(`/api/v1/datasets/${datasetId}/measurement`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export function getDataset(datasetId: string): Promise<DatasetVersion> {
  return requestJson<DatasetVersion>(`/api/v1/datasets/${datasetId}`)
}

export function getMeasurement(
  datasetId: string,
  version?: number,
): Promise<MeasurementVersion> {
  const url = version
    ? `/api/v1/datasets/${datasetId}/measurement?version=${version}`
    : `/api/v1/datasets/${datasetId}/measurement`
  return requestJson<MeasurementVersion>(url)
}

export function mergeDatasets(
  datasetId: string,
  targetDatasetId: string,
  subjectKey: string,
  waveKey: string | null,
): Promise<DatasetMergeResponse> {
  const body = {
    target_dataset_id: targetDatasetId,
    subject_key: subjectKey,
    wave_key: waveKey,
  }
  return requestJson<DatasetMergeResponse>(`/api/v1/datasets/${datasetId}/merge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}
