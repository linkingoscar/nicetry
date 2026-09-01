import type {
  AnalysisSampleVersion,
  AnalysisSampleVersionRequest,
  DataQualityRun,
  DataQualityRunRequest,
  QualityCasePage,
} from '../types'
import { requestJson } from './client'

export function runDataQuality(
  datasetId: string,
  request: DataQualityRunRequest,
): Promise<DataQualityRun> {
  return requestJson<DataQualityRun>(`/api/v1/datasets/${datasetId}/quality-runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export function listDataQualityRuns(datasetId: string): Promise<DataQualityRun[]> {
  return requestJson<DataQualityRun[]>(`/api/v1/datasets/${datasetId}/quality-runs`)
}

export function getQualityCases(
  datasetId: string,
  qualityRunId: string,
  offset = 0,
  limit = 100,
): Promise<QualityCasePage> {
  return requestJson<QualityCasePage>(
    `/api/v1/datasets/${datasetId}/quality-runs/${qualityRunId}/cases?offset=${offset}&limit=${limit}`,
  )
}

export function createAnalysisSample(
  datasetId: string,
  request: AnalysisSampleVersionRequest,
): Promise<AnalysisSampleVersion> {
  return requestJson<AnalysisSampleVersion>(`/api/v1/datasets/${datasetId}/sample-versions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}

export function listAnalysisSamples(datasetId: string): Promise<AnalysisSampleVersion[]> {
  return requestJson<AnalysisSampleVersion[]>(`/api/v1/datasets/${datasetId}/sample-versions`)
}

export function getSampleCases(
  datasetId: string,
  sampleId: string,
  offset = 0,
  limit = 100,
): Promise<QualityCasePage> {
  return requestJson<QualityCasePage>(
    `/api/v1/datasets/${datasetId}/sample-versions/${sampleId}/cases?offset=${offset}&limit=${limit}`,
  )
}
