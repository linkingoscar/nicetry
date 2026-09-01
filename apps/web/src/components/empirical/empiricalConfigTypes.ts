import type { DiaryMultilevelOptions, LongitudinalPanelOptions } from '../../types'

export interface EmpiricalConfigValue {
  procedure: import('../../types/empirical-types').EmpiricalProcedure
  analysisVariableIds: string[]
  constructIds: string[]
  factorCount: number
  groupVariableId: string | null
  aggregationVariableId: string | null
  outcomeVariableId: string | null
  predictorVariableIds: string[]
  controlVariableIds: string[]
  responseSurfacePredictorIds: string[]
  correlationMethod: 'pearson' | 'spearman' | 'partial'
  correlationPAdjust: 'none' | 'holm' | 'BH'
  groupOmnibusPAdjust: 'none' | 'holm' | 'BH'
  multiplicityPAdjust: 'none' | 'holm' | 'BH'
  confidenceLevel: number
  multiplicityFamilyId: string
  rotation: 'varimax' | 'promax'
  factorCountMethod: 'kaiser' | 'parallel_analysis' | 'manual'
  parallelIterations: number
  randomSeed: number
  sampleVersionId: string | null
  longitudinalPanel: LongitudinalPanelOptions | null
  diaryMultilevel: DiaryMultilevelOptions | null
}
