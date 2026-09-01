import type {
  DiaryDsemDiagnostics,
  DiaryDsemPlotParameter,
  DiaryDsemPosteriorEffect,
  DiaryFixedEffect,
} from './longitudinal-evidence'

export interface DiaryAdvancedEvidence {
  countModel?: 'standard' | 'zero_inflated' | 'hurdle'
  zeroProcessPredictors?: 'intercept_only' | 'shared'
  zeroProcessEffects?: DiaryFixedEffect[]
  countModelComparison?: Array<{
    model: string
    label: string
    aic: number | null
    bic: number | null
    logLikelihood: number | null
    parameterCount: number | null
    converged: boolean
  }>
  posteriorEffects?: DiaryDsemPosteriorEffect[]
  mcmcDiagnostics?: DiaryDsemDiagnostics
  posteriorPredictive?: {
    yBayesianRSquared: number | null
    xBayesianRSquared: number | null
    checks?: Array<{
      equation: 'Y' | 'X'
      statistic: string
      observed: number | null
      replicatedMedian: number | null
      replicatedLower: number | null
      replicatedUpper: number | null
      confidenceLevelSource: 'method_definition'
      bayesianPValue: number | null
    }>
  }
  priorPredictive?: {
    method: string
    checks: Array<{
      equation: 'Y' | 'X'
      statistic: string
      observed: number | null
      replicatedMedian: number | null
      replicatedLower: number | null
      replicatedUpper: number | null
      confidenceLevelSource: 'method_definition'
      observedWithinInterval: boolean
    }>
  }
  posteriorDraws?: DiaryDsemPlotParameter[]
  priorSensitivity?: {
    method: string
    scenarios: Array<{
      scenario: string
      priorMeanSd: number
      reweightingEffectiveSampleSize: number | null
      effects: Array<{
        id: string
        estimate: number | null
        lower: number | null
        upper: number | null
        absoluteChange: number | null
        inferenceChanged: boolean
      }>
    }>
  }
}
