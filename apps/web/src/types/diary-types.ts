import type { DiaryAdvancedEvidence } from './diary-advanced-evidence'
import type {
  DiaryCenteringProtocol,
  DiaryDistributionDiagnostics,
  DiaryFixedEffect,
  DiaryTimeTrendTest,
} from './longitudinal-evidence'
import type { LongitudinalPanelResult } from './longitudinal-types'

export interface DiaryMultilevelResult extends DiaryAdvancedEvidence {
  available: boolean
  analysisType: 'lmm' | 'glmm' | 'mediation' | 'bayesian_dsem'
  modelLabel: string
  sampleSize: number
  personCount: number
  validForInterpretation: boolean
  diagnostics: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  sampleFlow: { original: number; included: number; excluded: number; missingMethod: string }
  observationsPerPerson?: { minimum: number; median: number; maximum: number }
  crossClassCount?: number | null
  formula?: string
  outcomeFamily?: 'gaussian' | 'binomial' | 'poisson' | 'negative_binomial'
  linkFunction?: string
  effectScale?: string
  clusterStructure?: 'nested' | 'cross_classified'
  crossClassVariableId?: string | null
  exposureVariableId?: string | null
  centering?: string
  withinPredictorId?: string
  betweenPredictorId?: string | null
  temporalEffect?: 'contemporaneous' | 'lagged' | 'both'
  lagOrder?: number
  laggedPredictorId?: string | null
  timeGapId?: string | null
  crossLevelInteractionIds?: string[]
  centeringProtocol?: DiaryCenteringProtocol
  timeTrendTest?: DiaryTimeTrendTest | null
  fixedEffects?: DiaryFixedEffect[]
  varianceComponents?: Array<{
    group: string; term: string; pairedTerm: string | null
    variance: number | null; standardDeviation: number | null
  }>
  icc?: number | null
  marginalRSquared?: number | null
  conditionalRSquared?: number | null
  residualStructure?: string
  ar1?: number | null
  singular?: boolean
  distributionDiagnostics?: DiaryDistributionDiagnostics
  mediationType?: '1-1-1' | '2-1-1'
  paths?: Array<{
    id: string; lhs: string; rhs: string | null; estimate: number | null
    standardizedEstimate: number | null; standardError: number | null
    statistic: number | null; pValue: number | null; lower: number | null; upper: number | null
  }>
  indirectEffects?: Array<{
    id: string; lhs: string; rhs: null; estimate: number | null
    standardizedEstimate: number | null; standardError: number | null
    statistic: number | null; pValue: number | null; lower: number | null; upper: number | null
  }>
  fitIndices?: LongitudinalPanelResult['fitIndices']
  dataQuality?: {
    personCount: number
    observedPromptRows: number
    expectedObservationsPerPerson: number | null
    overallComplianceRate: number | null
    personCompliance: {
      minimum: number | null
      median: number | null
      maximum: number | null
      belowThresholdCount: number
      threshold: number
    }
    responseLatency: null | {
      n: number
      mean: number | null
      median: number | null
      p95: number | null
      minimum: number | null
      maximum: number | null
      outsideWindowCount: number
    }
    exclusionRules: {
      excludeLowCompliance: boolean
      excludeOutOfWindow: boolean
    }
  }
  multilevelReliability?: Array<{
    label: string
    itemIds: string[]
    observationCount: number
    personCount: number
    withinAlpha: number | null
    betweenAlpha: number | null
    meanItemIcc: number | null
    itemIccs: Array<{ itemId: string; icc: number | null }>
    method: string
  }>
  missingData?: {
    strategy: 'multilevel_mi'
    imputationCount: number
    iterations?: number
    seed?: number
    loggedEventCount?: number
    pooling?: string
    message?: string
    missingCounts?: Array<{ variableId: string; missing: number }>
  }
  robustnessChecks?: Array<{
    scenario: string
    analysisType: 'lmm' | 'glmm' | 'mediation' | 'bayesian_dsem'
    modelLabel: string
    sampleSize: number
    personCount: number
    temporalEffect: string | null
    residualStructure: string | null
    randomSlope: boolean | null
    validForInterpretation: boolean
    fixedEffects?: DiaryMultilevelResult['fixedEffects']
    indirectEffects?: DiaryMultilevelResult['indirectEffects']
  }>
  powerAnalysis?: DiaryPowerResult
  priorSpecification?: Record<string, unknown>
  methodNotice?: string
  provenance: Record<string, unknown>
}

export interface DiaryPowerResult {
  method: string
  targetParameter: string
  targetPower: number
  alpha: number
  replications: number
  seed: number
  results: Array<{
    personCount: number
    observationsPerPerson: number
    totalObservations: number
    convergedReplications: number
    failedReplications: number
    singularReplications: number
    convergenceRate: number
    averageEstimate: number | null
    bias: number | null
    empiricalStandardError: number | null
    averageStandardError: number | null
    coverage: number | null
    coverageMcse: number | null
    powerConditionalOnConvergence: number | null
    power: number | null
    powerMcse: number | null
  }>
  recommendation: DiaryPowerResult['results'][number] | null
  validForPlanning: boolean
  failureRule: string
  assumptions: Record<string, unknown>
  provenance: Record<string, unknown>
}
