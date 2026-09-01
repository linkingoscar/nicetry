import type { components } from './generated-api'

type Schemas = components['schemas']

export type ExperimentalDesignSpec = Schemas['ExperimentalDesignSpec']
export type MultilevelModelSpec = Schemas['MultilevelModelSpec']
export type MultipleImputationSpec = Schemas['MultipleImputationSpec']
export type PowerAnalysisSpec = Schemas['PowerAnalysisSpec']
export type QuestionnaireMeasurementSpec = Schemas['QuestionnaireMeasurementSpec']

export type AdvancedAnalysisSpec =
  | ExperimentalDesignSpec
  | MultilevelModelSpec
  | MultipleImputationSpec
  | PowerAnalysisSpec
  | QuestionnaireMeasurementSpec

export type AdvancedAnalysisFamily = AdvancedAnalysisSpec['family']
export type ValidationLevel = 'unvalidated' | 'internally_validated' | 'externally_validated'
export type CapabilityMaturity = 'experimental' | 'validated' | 'reviewer_ready' | 'publication_ready'
export type PublicationEligibility = 'ineligible' | 'conditional' | 'eligible'
export type CapabilityValidationEvidence = Schemas['CapabilityValidationEvidence']
/**
 * The API contract requires all three maturity fields.  Keep them optional in
 * this presentation model so persisted local drafts and narrow test fixtures
 * from older clients render with the conservative experimental/not-eligible
 * fallback until they are refreshed from the server.
 */
export type AdvancedCapabilitySlice = Omit<
  Schemas['AdvancedCapabilitySliceResponse'],
  'validationLevel' | 'maturityLevel' | 'publicationEligibility' | 'publicationEligibilityReason' | 'validationEvidence'
> & Partial<Pick<
  Schemas['AdvancedCapabilitySliceResponse'],
  'validationLevel' | 'maturityLevel' | 'publicationEligibility' | 'publicationEligibilityReason' | 'validationEvidence'
>>

/** Capability responses remain presentation view models until execution endpoints are implemented. */
export interface AdvancedAnalysisCapability {
  family: AdvancedAnalysisFamily
  /** The concrete registered slice selected from the context capability catalog. */
  sliceId?: string
  label: string
  status: 'planned' | 'experimental' | 'supported'
  specVersion: string
  resultVersion: string
  plannedEngine: string
  minimumValidation: string[]
  executionAvailable: boolean
  slices: AdvancedCapabilitySlice[]
  validationLevel?: ValidationLevel
  maturityLevel?: CapabilityMaturity
  publicationEligibility?: PublicationEligibility
  publicationEligibilityReason?: string
  validationEvidence?: CapabilityValidationEvidence
}

export interface AdvancedAnalysisValidation {
  valid: true
  family: AdvancedAnalysisFamily
  capabilityId: string
  sliceId?: string | null
  sliceStatus: 'planned' | 'experimental' | 'supported'
  implementationStatus: string
  executionAvailable: boolean
  validationLevel?: ValidationLevel
  maturityLevel?: CapabilityMaturity
  publicationEligibility?: PublicationEligibility
  publicationEligibilityReason?: string
  validationEvidence?: CapabilityValidationEvidence
  spec: AdvancedAnalysisSpec
  warnings: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
}

export type AdvancedJobResponse = Schemas['AdvancedJobResponse']
export type AdvancedResultResponse = Schemas['AdvancedResultResponse']

export type AdvancedPlot = Schemas['AdvancedPlotResponse']
export type ExtendedAdvancedResultResponse = AdvancedResultResponse
