import type { DiaryDsemOptions } from './longitudinal-evidence'

export interface DiaryMultilevelOptions {
  analysisType: 'lmm' | 'glmm' | 'mediation' | 'bayesian_dsem'
  subjectVariableId: string
  timeVariableId: string
  outcomeVariableId: string
  predictorVariableId: string
  mediatorVariableId: string | null
  level2CovariateIds: string[]
  controlVariableIds: string[]
  randomSlope: boolean
  residualStructure: 'independent' | 'ar1'
  outcomeFamily: 'gaussian' | 'binomial' | 'poisson' | 'negative_binomial'
  countModel: 'standard' | 'zero_inflated' | 'hurdle'
  zeroProcessPredictors: 'intercept_only' | 'shared'
  distributionDiagnosticSimulations: number
  distributionDiagnosticSeed: number
  clusterStructure: 'nested' | 'cross_classified'
  crossClassVariableId: string | null
  exposureVariableId: string | null
  centering: 'person_mean' | 'grand_mean' | 'none'
  mediationType: '1-1-1' | '2-1-1'
  temporalEffect: 'contemporaneous' | 'lagged' | 'both'
  lagOrder: number
  expectedTimeInterval: number | null
  timeIntervalTolerance: number
  includeLinearTime: boolean
  includeQuadraticTime: boolean
  timeOriginStrategy: 'sample_mean' | 'first_observed' | 'custom'
  customTimeOrigin: number | null
  level2ModeratorVariableId: string | null
  expectedObservationsPerPerson: number | null
  minimumComplianceRate: number
  excludeLowCompliance: boolean
  responseLatencyVariableId: string | null
  minimumResponseLatency: number | null
  maximumResponseLatency: number | null
  excludeOutOfWindow: boolean
  reliabilityConstructs: Array<{ label: string; itemIds: string[] }>
  missingStrategy: 'complete_cases' | 'multilevel_mi'
  imputationCount: number
  imputationIterations: number
  runRobustnessChecks: boolean
  powerAnalysis: DiaryPowerOptions | null
  dsem: DiaryDsemOptions | null
}

export interface DiaryPowerOptions {
  personCounts: number[]
  observationsPerPerson: number[]
  replications: number
  targetPower: number
  alpha: number
  withinEffect: number
  betweenEffect: number
  randomInterceptSd: number
  randomSlopeSd: number
  residualSd: number
  predictorBetweenSd: number
  predictorWithinSd: number
  residualAr1: number
  seed: number
}
