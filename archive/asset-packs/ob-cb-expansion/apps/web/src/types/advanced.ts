import type { components } from './generated-api'

type Schemas = components['schemas']

export type ExperimentalDesignSpec = Schemas['ExperimentalDesignSpec']
export type MultilevelModelSpec = Schemas['MultilevelModelSpec']
export type LongitudinalModelSpec = Schemas['LongitudinalModelSpec']
export type MultipleImputationSpec = Schemas['MultipleImputationSpec']
export type PowerAnalysisSpec = Schemas['PowerAnalysisSpec']
export type QuestionnaireMeasurementSpec = Schemas['QuestionnaireMeasurementSpec']

export type AdvancedAnalysisSpec =
  | ExperimentalDesignSpec
  | MultilevelModelSpec
  | LongitudinalModelSpec
  | MultipleImputationSpec
  | PowerAnalysisSpec
  | QuestionnaireMeasurementSpec

export type AdvancedAnalysisFamily = AdvancedAnalysisSpec['family']
export type AdvancedCapabilitySlice = Schemas['AdvancedCapabilitySliceResponse']

/** Capability responses remain presentation view models until execution endpoints are implemented. */
export interface AdvancedAnalysisCapability {
  family: AdvancedAnalysisFamily
  label: string
  status: 'planned' | 'experimental' | 'supported'
  specVersion: string
  resultVersion: string
  plannedEngine: string
  minimumValidation: string[]
  executionAvailable: boolean
  slices: AdvancedCapabilitySlice[]
}

export interface AdvancedAnalysisValidation {
  valid: true
  family: AdvancedAnalysisFamily
  capabilityId: string
  sliceId?: string | null
  sliceStatus: 'planned' | 'experimental' | 'supported'
  implementationStatus: string
  executionAvailable: boolean
  spec: AdvancedAnalysisSpec
  warnings: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
}

export type AdvancedJobResponse = Schemas['AdvancedJobResponse']
export type AdvancedResultResponse = Schemas['AdvancedResultResponse']

export type AdvancedPlot = Schemas['AdvancedPlotResponse']
export type ExtendedAdvancedResultResponse = AdvancedResultResponse
