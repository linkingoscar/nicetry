import type { components } from './generated-api'

type Schemas = components['schemas']

export type StudyIntent = 'plan' | 'analyze'

/** Internal adapter for the existing empirical engine segments. */
export type AnalysisParadigm = 'questionnaire' | 'longitudinal' | 'diary'

export type TimeStructure = 'cross_sectional' | 'panel' | 'intensive_longitudinal'

export type DependenceStructure = 'independent' | 'nested'

export type StudyDesign = 'observational' | 'randomized' | 'quasi_experimental'

export interface StudyContext {
  schemaVersion: '1.0.0'
  timeStructure: TimeStructure
  dependenceStructure: DependenceStructure
  design: StudyDesign
}

export interface StudyContextRecord extends StudyContext {
  projectId: string
  revision: number
  updatedAt: string
}

export interface DatasetStructureInput {
  context: StudyContext
  subjectId?: string | null
  clusterId?: string | null
  timeId?: string | null
  groupId?: string | null
  treatmentId?: string | null
  overrideReason?: string | null
}

export interface DatasetStructureRecord extends DatasetStructureInput {
  datasetVersionId: string
  revision: number
  updatedAt: string
}

export type DatasetRoleBindings = Schemas['DatasetRoleBindings']
export type DatasetStructureVersion = Schemas['DatasetStructureVersion']
export type StructureValidationResponse = Schemas['StructureValidationResponse']

export const DEFAULT_STUDY_CONTEXT: StudyContext = {
  schemaVersion: '1.0.0',
  timeStructure: 'cross_sectional',
  dependenceStructure: 'independent',
  design: 'observational',
}

export const STUDY_CONTEXT_STORAGE_KEY = 'researchpath_study_context_v1'
export const STUDY_INTENT_STORAGE_KEY = 'researchpath_study_intent_v1'

export function parseStudyContext(value: string | null): StudyContext {
  if (!value) return DEFAULT_STUDY_CONTEXT
  try {
    const parsed = JSON.parse(value) as Partial<StudyContext>
    const timeStructure = parsed.timeStructure
    const dependenceStructure = parsed.dependenceStructure
    const design = parsed.design
    if (
      parsed.schemaVersion === '1.0.0'
      && (timeStructure === 'cross_sectional' || timeStructure === 'panel' || timeStructure === 'intensive_longitudinal')
      && (dependenceStructure === 'independent' || dependenceStructure === 'nested')
      && (design === 'observational' || design === 'randomized' || design === 'quasi_experimental')
    ) {
      return { schemaVersion: '1.0.0', timeStructure, dependenceStructure, design }
    }
  } catch {
    // Invalid or pre-versioned state falls back to a safe, explicit default.
  }
  return DEFAULT_STUDY_CONTEXT
}
