export interface DiaryCenteringProtocol {
  level1Predictor: {
    strategy: string
    level1Formula: string
    level2Formula: string | null
    personMeanReintroduced: boolean
    grandMeanWeighting: string | null
    level1Reference: number | null
    level2Reference: number | null
  }
  level2Moderator: null | {
    strategy: string
    formula: string
    grandMeanWeighting: string
    reference: number | null
    centeredVariableId: string
  }
  crossLevelInteractions: string[]
  time: {
    originStrategy: string
    originValue: number | null
    centeredVariableId: string
    linearTerm: string
    quadraticTerm: string | null
    observedMinimum: number | null
    observedMaximum: number | null
  }
  interpretation: string
}

export interface DiaryTimeTrendTest {
  terms: string[]
  statistic: number | null
  degreesOfFreedom: number
  pValue: number | null
  method: string
  originStrategy: string
  originValue: number | null
  linearSlopeAtOrigin: number | null
  quadraticCoefficient: number | null
  turningPoint: number | null
  turningPointInObservedRange: boolean | null
}

export interface DiaryDistributionDiagnostics {
  pearsonDispersion: number | null
  observedZeroRate: number | null
  expectedZeroRate: number | null
  zeroRateDifference: number | null
  simulationCount?: number
  dispersionRatio?: number | null
  dispersionPValue?: number | null
  zeroInflationPValue?: number | null
  diagnosticMethod?: string
}

export interface DiaryDsemOptions {
  chains: number
  iterations: number
  warmup: number
  thin: number
  priorMeanSd: number
  priorScale: number
  randomDynamicSlopes: boolean
  plotDrawsPerChain: number
  predictiveReplications: number
  runPriorSensitivity: boolean
  seed: number
}

export interface DiaryFixedEffect {
  term: string
  label: string
  estimate: number | null
  standardError: number | null
  degreesOfFreedom: number | null
  statistic: number | null
  pValue: number | null
  lower: number | null
  upper: number | null
  fractionMissingInformation?: number | null
  exponentiatedEstimate?: number | null
  exponentiatedLower?: number | null
  exponentiatedUpper?: number | null
}

export interface DiaryDsemPosteriorEffect {
  id: string
  label: string
  estimate: number | null
  posteriorSd: number | null
  lower: number | null
  upper: number | null
  probabilityPositive: number | null
  rHat: number | null
  effectiveSampleSize: number | null
  bulkEffectiveSampleSize: number | null
  tailEffectiveSampleSize: number | null
  mcseMean: number | null
}

export interface DiaryDsemPlotParameter {
  id: string
  label: string
  chains: Array<{
    chain: number
    iterations: number[]
    values: number[]
  }>
}

export interface DiaryDsemDiagnostics {
  chains: number
  iterationsPerChain: number
  warmupPerChain: number
  thin: number
  retainedPerChain: number
  maximumRHat: number | null
  minimumEffectiveSampleSize: number | null
  minimumBulkEffectiveSampleSize: number | null
  minimumTailEffectiveSampleSize: number | null
  effectiveSampleSizeThreshold: number | null
  diagnosticMethod: string
  stationarity: {
    yAutoregressiveWithinUnitInterval: boolean
    xAutoregressiveWithinUnitInterval: boolean
  }
}

export interface LongitudinalGrowthModel {
  growthShape: 'linear' | 'quadratic'
  timeOrigin: number
  timeLoadings: number[]
  interpretation: string
  identification: {
    converged: boolean
    postCheckPassed: boolean
    latentCovarianceMinimumEigenvalue: number | null
    negativeGrowthVarianceCount: number
    valid: boolean
  }
  components: Array<{
    lhs: string
    operator: '~1' | '~~'
    rhs: string | null
    estimate: number | null
    standardizedEstimate: number | null
    standardError: number | null
    pValue: number | null
    lower: number | null
    upper: number | null
  }>
}

export interface LongitudinalCmbSensitivity {
  requested: boolean
  available: boolean
  validForInterpretation: boolean
  method: string
  orthogonalToSubstantiveFactors?: boolean
  markerItemId?: string
  indicatorCount?: number
  averageStandardizedVarianceShare?: number | null
  changedInferenceCount?: number
  interpretation?: string
  identification?: {
    converged: boolean
    postCheckPassed: boolean
    negativeVarianceCount: number
    latentCovarianceMinimumEigenvalue: number | null
    informationMinimumEigenvalueRatio: number | null
    informationFullRank: boolean
    valid: boolean
  }
  methodLoadings?: Array<{
    itemId: string
    loading: number | null
    standardizedLoading: number | null
    standardizedVarianceShare: number | null
    pValue: number | null
  }>
  pathChanges?: Array<{
    id: string
    pathType: 'autoregressive' | 'cross_lagged'
    direction: string
    fromWave: number
    toWave: number
    baselineEstimate: number | null
    adjustedEstimate: number | null
    absoluteChange: number | null
    relativeChange: number | null
    baselinePValue: number | null
    adjustedPValue: number | null
    signChanged: boolean
    inferenceChanged: boolean
    adjustedLower: number | null
    adjustedUpper: number | null
  }>
  diagnostics: Array<{
    code: string
    severity: 'info' | 'warning' | 'error'
    message: string
  }>
}
