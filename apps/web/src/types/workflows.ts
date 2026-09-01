import type { components } from './generated-api'

export type StudyPlanVersion = components['schemas']['StudyPlanVersion']
export type StudyPlanDatasetMapping = components['schemas']['StudyPlanDatasetMapping']
export type StudyPlanBinding = components['schemas']['StudyPlanBinding']
export type StudyPlanResultBinding = StudyPlanBinding & {
  status: 'current' | 'stale'
  currentEvidence: boolean
  staleReasons: string[]
  hypothesisIds?: string[]
  datasetSha256?: string
  sampleVersionId?: string
  sampleHash?: string
  measurementVersionId?: string
  measurementHash?: string
  specHash?: string
  declarationStatus?: 'declared' | 'deviated'
  deviationReason?: string | null
  publicationEligible?: boolean
}

export interface StudyPlanEvidenceGraph {
  schemaVersion: '2.0.0'
  studyPlanVersion: { id: string; hash: string; revision: number; status: 'frozen' }
  hypotheses: Array<{ id: string; estimandIds: string[] }>
  estimands: Array<{ id: string; quantity: string; hypothesisIds: string[] }>
  analysisDeclarations: Array<{
    id: string
    role: 'primary' | 'robustness' | 'exploratory'
    estimandIds: string[]
    capabilitySliceId: string
    requestedMethod: string
  }>
  resultBinding: StudyPlanResultBinding
  modelVersionId?: string
  edges?: Array<{ edgeId: string; from: string; to: string; hypothesisId?: string | null; estimand: string }>
  effectBindings?: Array<{
    effectId: string
    edgeIds: string[]
    hypothesisIds: string[]
    hypothesisId?: string | null
    estimand: string
  }>
}
export type ImputationPlanVersion = components['schemas']['ImputationPlanVersion']
export type ImputationCompatibilityResponse = components['schemas']['ImputationCompatibilityResponse']

export type ImputationPlanCreateRequest = components['schemas']['ImputationPlanCreateRequest']
