import type { DiaryMultilevelOptions } from './diary-contracts'
import type { AnalysisJob } from './job-types'
import type { LongitudinalPanelOptions } from './longitudinal-types'
import type { StudyPlanBinding } from './workflows'

export type EmpiricalProcedure =
  | 'descriptives' | 'frequencies' | 'missing' | 'correlation' | 'reliability'
  | 'efa' | 'cfa' | 'validity' | 'common_method' | 'invariance' | 'groups'
  | 'aggregation' | 'regression' | 'relative_importance' | 'response_surface' | 'longitudinal' | 'diary'

export interface EmpiricalAnalysisOptions {
  procedure?: EmpiricalProcedure | null
  analysisVariableIds?: string[]
  constructIds?: string[]
  contextHash?: string | null
  sampleVersionId?: string | null
  factorCount: number
  groupVariableId: string | null
  aggregationVariableId: string | null
  outcomeVariableId: string | null
  predictorVariableIds: string[]
  controlVariableIds: string[]
  responseSurfacePredictorIds?: string[]
  correlationMethod?: 'pearson' | 'spearman' | 'partial'
  correlationPAdjust?: 'none' | 'holm' | 'BH'
  groupOmnibusPAdjust?: 'none' | 'holm' | 'BH'
  multiplicityPAdjust?: 'none' | 'holm' | 'BH'
  confidenceLevel?: number
  multiplicityFamilyId?: string
  rotation?: 'varimax' | 'promax'
  factorCountMethod?: 'kaiser' | 'parallel_analysis' | 'manual'
  parallelIterations?: number
  randomSeed?: number
  contextTimeStructure?: 'cross_sectional' | 'panel' | 'intensive_longitudinal' | null
  contextDependenceStructure?: 'independent' | 'nested' | null
  contextDesign?: 'observational' | 'randomized' | 'quasi_experimental' | null
  applicableCapabilitySlices?: string[]
  studyPlanBinding?: StudyPlanBinding
  longitudinalPanel?: LongitudinalPanelOptions | null
  diaryMultilevel?: DiaryMultilevelOptions | null
}

export interface StatisticalMethodExecution {
  requestedMethod: string
  executedMethod: string
  fallbackApplied: boolean
  fallbackCode: string | null
  fallbackReason: string | null
  affectedOutputs: string[]
  interpretationBoundary: string | null
}

export interface EmpiricalAnalysisJob extends AnalysisJob {
  jobKind: 'empirical'
  measurementVersion: number | null
  measurementVersionId: string | null
  reportId: string
  warnings: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  options: EmpiricalAnalysisOptions
  metadata: Record<string, unknown> | null
}
