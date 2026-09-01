import type { StudyContext, StudyIntent } from '../types'
import {
  parseStudyContext,
  STUDY_CONTEXT_STORAGE_KEY,
  STUDY_INTENT_STORAGE_KEY,
} from '../types/study-context'
import type { WorkspaceView } from './workspaceStateTypes'

export const WORKSPACE_VIEW_STORAGE_KEY = 'researchpath_active_view'
export const ACTIVE_DATASET_STORAGE_KEY = 'researchpath_active_dataset_id'
export const ACTIVE_MEASUREMENT_VERSION_STORAGE_KEY = 'researchpath_active_measurement_version'

export function readStudyIntent(): StudyIntent | null {
  const saved = localStorage.getItem(STUDY_INTENT_STORAGE_KEY)
  if (saved === 'plan' || saved === 'analyze') return saved
  return localStorage.getItem(ACTIVE_DATASET_STORAGE_KEY) ? 'analyze' : null
}

export function writeStudyIntent(studyIntent: StudyIntent | null): void {
  if (studyIntent) localStorage.setItem(STUDY_INTENT_STORAGE_KEY, studyIntent)
  else localStorage.removeItem(STUDY_INTENT_STORAGE_KEY)
}

export function readStudyContext(): StudyContext {
  return parseStudyContext(localStorage.getItem(STUDY_CONTEXT_STORAGE_KEY))
}

export function writeStudyContext(studyContext: StudyContext): void {
  localStorage.setItem(STUDY_CONTEXT_STORAGE_KEY, JSON.stringify(studyContext))
}

export function readActiveView(): WorkspaceView {
  const saved = localStorage.getItem(WORKSPACE_VIEW_STORAGE_KEY)
  if (saved === 'advanced') return 'methods'
  return saved === 'data' || saved === 'empirical' || saved === 'model' || saved === 'methods' ? saved : 'data'
}

export function writeActiveView(activeView: WorkspaceView): void {
  localStorage.setItem(WORKSPACE_VIEW_STORAGE_KEY, activeView)
}

export function readActiveDatasetId(): string | null {
  return localStorage.getItem(ACTIVE_DATASET_STORAGE_KEY)
}

export function writeActiveDatasetId(activeDatasetId: string | null): void {
  if (activeDatasetId) {
    localStorage.setItem(ACTIVE_DATASET_STORAGE_KEY, activeDatasetId)
  } else {
    localStorage.removeItem(ACTIVE_DATASET_STORAGE_KEY)
  }
}

export function readActiveMeasurementVersion(): number | null {
  const saved = localStorage.getItem(ACTIVE_MEASUREMENT_VERSION_STORAGE_KEY)
  return saved ? Number(saved) : null
}

export function writeActiveMeasurementVersion(activeMeasurementVersion: number | null): void {
  if (activeMeasurementVersion !== null) {
    localStorage.setItem(ACTIVE_MEASUREMENT_VERSION_STORAGE_KEY, String(activeMeasurementVersion))
  } else {
    localStorage.removeItem(ACTIVE_MEASUREMENT_VERSION_STORAGE_KEY)
  }
}
