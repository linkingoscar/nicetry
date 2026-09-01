import type {
  DatasetStructureInput,
  DatasetStructureRecord,
  DatasetRoleBindings,
  DatasetStructureVersion,
  StructureValidationResponse,
  StudyContext,
  StudyContextRecord,
} from '../types/study-context'
import { requestJson } from './client'

export function getStudyContext(projectId: string): Promise<StudyContextRecord> {
  return requestJson(`/api/v1/projects/${encodeURIComponent(projectId)}/study-context`)
}

export function saveStudyContext(
  projectId: string,
  context: StudyContext,
  expectedRevision?: number | null,
): Promise<StudyContextRecord> {
  return requestJson(`/api/v1/projects/${encodeURIComponent(projectId)}/study-context`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(expectedRevision === undefined ? context : { expectedRevision, context }),
  })
}

export function getDatasetStructure(datasetId: string): Promise<DatasetStructureRecord> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/study-structure`)
}

export function saveDatasetStructure(
  datasetId: string,
  structure: DatasetStructureInput,
): Promise<DatasetStructureRecord> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/study-structure`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(structure),
  })
}

export function validateDatasetStructure(
  datasetId: string,
  studyContextVersionId: string,
  roles: DatasetRoleBindings,
): Promise<StructureValidationResponse> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/study-structure/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studyContextVersionId, roles }),
  })
}

export function createDatasetStructureVersion(
  datasetId: string,
  request: {
    expectedRevision?: number | null
    studyContextVersionId: string
    roles: DatasetRoleBindings
    overrideReason?: string | null
  },
): Promise<DatasetStructureVersion> {
  return requestJson(`/api/v1/datasets/${encodeURIComponent(datasetId)}/study-structures`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
}
