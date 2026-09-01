import type { components } from './generated-api'

type Schemas = components['schemas']

export type ResolvedAnalysisContext = Schemas['ResolvedAnalysisContext']
export type ApplicableCapability = Schemas['ApplicableCapability']
export type ApplicableCapabilitiesResponse = Schemas['ApplicableCapabilitiesResponse']
export type AnalysisDraft = Schemas['AnalysisDraft']
export type AnalysisDraftMutation = Schemas['AnalysisDraftMutation']
export type AnalysisDraftCreateRequest = Schemas['AnalysisDraftCreateRequest']
export type DatasetRoleBindings = Schemas['DatasetRoleBindings']
export type StructureProfile = Schemas['StructureProfile']

export type AnalysisContextQuery = {
  datasetId: string
  measurementVersion?: number | null
  sampleVersionId?: string | null
  imputationVersionId?: string | null
}
