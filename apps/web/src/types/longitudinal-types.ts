import type {
  LongitudinalCmbSensitivity,
  LongitudinalGrowthModel,
} from './longitudinal-evidence'

export interface LongitudinalPanelWave {
  label: string
  timeValue: number
  xVariableId: string | null
  yVariableId: string | null
  xItemIds: string[]
  yItemIds: string[]
}

export interface LongitudinalPanelOptions {
  modelType: 'clpm' | 'ri_clpm' | 'lcm_sr'
  measurementMode: 'observed_scores' | 'latent_items'
  subjectVariableId: string
  waves: LongitudinalPanelWave[]
  estimator: 'ML' | 'MLR' | 'WLSMV'
  missing: 'fiml' | 'complete_cases'
  constrainAcrossTime: boolean
  growthShape: 'linear' | 'quadratic'
  indicatorScale: 'continuous' | 'ordinal'
  invarianceLevel: 'none' | 'configural' | 'metric' | 'scalar' | 'strict'
  partialInvariancePositions: string[]
  cmbSensitivity: 'none' | 'global_ulmc'
  compareCompetingModels: boolean
  runRobustnessChecks: boolean
  powerAnalysis: LongitudinalPowerOptions | null
}

export interface LongitudinalPowerOptions {
  sampleSizes: number[]
  replications: number
  targetPower: number
  alpha: number
  autoregressiveX: number
  autoregressiveY: number
  crossLaggedXToY: number
  crossLaggedYToX: number
  icc: number
  randomInterceptCorrelation: number
  withinCorrelation: number
  reliability: number
  estimateMeasurementError: boolean
  seed: number
}

export interface LongitudinalPanelResult {
  available: boolean
  modelType: 'clpm' | 'ri_clpm' | 'lcm_sr'
  modelLabel: string
  measurementMode?: 'observed_scores' | 'latent_items'
  subjectVariableId: string
  subjectLabel: string
  constructLabels: { x: string; y: string }
  waveCount: number
  sampleSize: number
  estimator: string
  missingMethod: string
  constrainedAcrossTime: boolean
  validForInterpretation: boolean
  causalNotice: string
  fitIndices: {
    chiSquare: number | null
    degreesOfFreedom: number | null
    pValue: number | null
    cfi: number | null
    tli: number | null
    rmsea: number | null
    srmr: number | null
    aic: number | null
    bic: number | null
  }
  paths: Array<{
    id: string
    outcome: string
    predictor: string
    fromWave: number
    toWave: number
    pathType: 'autoregressive' | 'cross_lagged'
    direction: string
    estimate: number | null
    standardizedEstimate: number | null
    standardError: number | null
    statistic: number | null
    pValue: number | null
    lower: number | null
    upper: number | null
  }>
  growthModel?: LongitudinalGrowthModel | null
  cmbSensitivity?: LongitudinalCmbSensitivity | null
  waveSampleFlow: Array<{
    label: string
    timeValue: number
    observed: number
    retainedFromPrevious: number
    attritionFromPrevious: number
    reenteredFromPrevious: number
  }>
  diagnostics: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  measurementInvariance?: {
    requestedLevel: 'configural' | 'metric' | 'scalar' | 'strict'
    selectedLevel: 'configural' | 'metric' | 'scalar' | 'strict'
    indicatorScale: 'continuous' | 'ordinal'
    partialPositions: string[]
    criteriaSource: string
    models: Array<{
      level: 'configural' | 'metric' | 'scalar' | 'strict'
      label: string
      converged: boolean
      sampleSize: number
      fitIndices: LongitudinalPanelResult['fitIndices']
    }>
    comparisons: Array<{
      from: string
      to: string
      deltaCfi: number | null
      deltaRmsea: number | null
      deltaSrmr: number | null
      chiSquareDifference: number | null
      degreesOfFreedomDifference: number | null
      pValue: number | null
      passesPracticalCriteria: boolean
      criteria: string
    }>
  }
  competingModels?: Array<{
    modelType: 'clpm' | 'ri_clpm' | 'lcm_sr'
    modelLabel: string
    converged: boolean
    fitIndices: LongitudinalPanelResult['fitIndices']
  }>
  robustnessChecks?: Array<{
    scenario: string
    modelType: 'clpm' | 'ri_clpm' | 'lcm_sr'
    estimator: string
    missingMethod: string
    constrainedAcrossTime: boolean
    sampleSize: number
    validForInterpretation: boolean
    fitIndices: LongitudinalPanelResult['fitIndices']
    crossLaggedPaths: LongitudinalPanelResult['paths']
  }>
  powerAnalysis?: LongitudinalPowerResult
  provenance: Record<string, unknown>
}

export interface LongitudinalPowerResult {
  method: string
  targetPower: number
  alpha: number
  replications: number
  seed: number
  results: Array<{
    direction: 'x_to_y' | 'y_to_x'
    directionLabel: string
    sampleSize: number
    timePoints: number
    populationValue: number | null
    averageEstimate: number | null
    bias: number | null
    empiricalStandardError: number | null
    averageStandardError: number | null
    mse: number | null
    coverage: number | null
    coverageMcse: number | null
    power: number | null
    powerMcse: number | null
  }>
  recommendationGrid: Array<{
    sampleSize: number
    minimumDirectionalPower: number | null
    meetsTarget: boolean
  }>
  recommendedSampleSize: number | null
  estimationProblems: Array<Record<string, unknown>>
  warnings: string[]
  validForPlanning: boolean
  assumptions: Record<string, unknown>
  provenance: Record<string, unknown>
}
