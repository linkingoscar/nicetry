export interface ConfidenceInterval {
  level: number
  lower: number
  upper: number
  method: string
  replicates?: number
  seed?: number
}

export interface JohnsonNeymanResult {
  available: boolean
  reason?: string
  lower?: number
  upper?: number
  boundaries?: number[]
  observedBoundaries?: number[]
  observedMinimum: number
  observedMaximum: number
  confidenceLevel?: number
  criticalValue?: number
  method?: string
  grid?: Array<{
    moderatorValue: number
    effect: number
    standardError: number
    statistic: number
    pValue: number
    lower: number
    upper: number
    significant: boolean
  }>
  regions?: Array<{
    lower: number
    upper: number
    status: 'positive' | 'negative' | 'not_significant'
    effectAtMidpoint: number
  }>
}

export interface Effect {
  id: string
  type: 'path' | 'direct' | 'indirect' | 'total' | 'interaction' | 'conditional' | 'index' | 'contrast'
  label: string
  estimate: number
  edgeId?: string
  edgeIds?: string[]
  hypothesisIds?: string[]
  hypothesisId?: string | null
  estimand?: string
  standardError?: number
  confidenceInterval?: ConfidenceInterval
}

export interface FitIndices {
  chiSquare: number | null
  df: number | null
  pValue: number | null
  cfi: number | null
  tli: number | null
  rmsea: number | null
  srmr: number | null
  robustChiSquare?: number | null
  robustDf?: number | null
  robustPValue?: number | null
  robustCfi?: number | null
  robustTli?: number | null
  robustRmsea?: number | null
}

export interface SemResult {
  publicationEligible?: boolean
  requiresManualReview?: boolean
  publicationEligibilityReasons?: string[]
  estimationStatus?: 'not_run' | 'succeeded' | 'failed' | 'non_converged' | 'boundary_solution'
  inferenceStatus?: 'not_available' | 'reliable' | 'needs_review' | 'not_reliable'
  publicationEligibility?: 'ineligible' | 'conditional' | 'eligible'
  numericReferenceMatrix?: Record<string, unknown>
  fitIndices: FitIndices
  modelStructure: {
    firstOrderLatents: string[]
    higherOrderLatents: string[]
  }
  loadings: Array<{
    latentId: string
    indicatorId: string
    level?: 'first_order' | 'higher_order'
    estimate: number
    standardError: number | null
    statistic: number | null
    pValue: number | null
    stdAll: number
    ciLower?: number | null
    ciUpper?: number | null
  }>
  paths: Array<{
    from: string
    to: string
    estimate: number
    standardError: number | null
    statistic: number | null
    pValue: number | null
    stdAll: number
    ciLower?: number | null
    ciUpper?: number | null
  }>
  reliability: Array<{
    latentId: string
    cronbachAlpha: number
    /** alpha 实际使用的完整案例数（listwise 口径，可能与主拟合 FIML 样本不同） */
    alphaSampleSize?: number | null
    mcdonaldOmega: number | null
    compositeReliability: number | null
    /** CR/ω 被抑制的原因（如 suppressed_correlated_residuals） */
    compositeReliabilityReason?: string | null
    ave: number
  }>
}

export interface InvarianceResult {
  estimator?: 'ML' | 'WLSMV'
  groupSizes?: Record<string, number>
  groupParameters?: Array<{
    group: string
    loadings: Array<{
      latentId: string
      indicatorId: string
      level: 'first_order' | 'higher_order'
      estimate: number
      standardError: number | null
      pValue: number | null
      stdAll: number
      ciLower?: number | null
      ciUpper?: number | null
    }>
    paths: Array<{
      from: string
      to: string
      estimate: number
      standardError: number | null
      pValue: number | null
      stdAll: number
      ciLower?: number | null
      ciUpper?: number | null
    }>
  }>
  pathComparisons?: Array<{
    from: string
    to: string
    groupA: string
    groupB: string
    estimateA: number
    estimateB: number
    difference: number
    standardError: number
    statistic: number | null
    pValue: number | null
    ciLower: number
    ciUpper: number
    method: string
  }>
  predictionPlots?: Array<{
    from: string
    to: string
    predictorLabel: string
    outcomeLabel: string
    confidenceLevel: number
    method: string
    groups: Array<{
      group: string
      xValues: number[]
      predictedValues: number[]
      ciLower: number[]
      ciUpper: number[]
    }>
  }>
  partialInvarianceReleases?: Array<{
    stage: 'metric' | 'scalar' | 'strict'
    constraint: 'loading' | 'intercept_or_threshold' | 'residual'
    latentId: string | null
    indicatorId: string
    rationale: string
    lavaanParameters: string[]
  }>
  latentMeans?: Array<{
    group: string
    latentId: string
    estimate: number
    standardError: number | null
    pValue: number | null
    ciLower: number | null
    ciUpper: number | null
    referenceGroup: boolean
  }>
  structuralComparison?: null | {
    model: 'structural'
    constraints: Array<'loadings' | 'intercepts' | 'thresholds' | 'regressions'>
    fitIndices: FitIndices
    deltaChiSquare: number | null
    deltaDf: number | null
    pValue: number | null
  }
  models: Array<{
    model: 'configural' | 'metric' | 'scalar' | 'strict'
    constraints?: Array<'loadings' | 'intercepts' | 'thresholds' | 'residuals'>
    releasedParameters?: string[]
    fitIndices: FitIndices
  }>
  comparisons: Array<{
    comparison: 'metric_vs_configural' | 'scalar_vs_metric' | 'strict_vs_scalar'
    deltaChiSquare: number | null
    deltaDf: number | null
    pValue: number | null
    deltaCfi: number | null
    deltaRmsea: number | null
    invarianceHolds: boolean | null
    evaluationStatus?: 'pass' | 'fail' | 'not_evaluable'
  }>
}
