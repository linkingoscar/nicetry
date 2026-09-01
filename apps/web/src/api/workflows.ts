import type { StudyPlanDatasetMapping, StudyPlanVersion } from '../types/workflows'
import { requestJson } from './client'

export function createStudyPlan(projectId: string, payload: Record<string, unknown>): Promise<StudyPlanVersion> {
  return requestJson(`/api/v1/projects/${encodeURIComponent(projectId)}/study-plans`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payload }),
  })
}

export function updateStudyPlan(planId: string, expectedRevision: number, payload: Record<string, unknown>): Promise<StudyPlanVersion> {
  return requestJson(`/api/v1/study-plans/${encodeURIComponent(planId)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ expectedRevision, payload }),
  })
}

export function freezeStudyPlan(planId: string): Promise<StudyPlanVersion> {
  return requestJson(`/api/v1/study-plans/${encodeURIComponent(planId)}/freeze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: '{}',
  })
}

export function mapStudyPlanDataset(
  planId: string,
  datasetVersionId: string,
  mapping: Record<string, unknown>,
  status: StudyPlanDatasetMapping['status'] = 'incomplete',
): Promise<StudyPlanDatasetMapping> {
  return requestJson(`/api/v1/study-plans/${encodeURIComponent(planId)}/map-dataset`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ datasetVersionId, mapping, status }),
  })
}
