export type NodeRole = 'x' | 'm' | 'y' | 'w' | 'z' | 'covariate'

export interface ModelNode {
  id: string
  variableId?: string
  label: string
  kind: 'observed' | 'scale_score' | 'latent'
  role: NodeRole
  dataType: 'continuous' | 'binary' | 'nominal' | 'ordinal'
  encoding?: VariableEncoding
}

export type VariableEncodingMethod =
  | 'as_is'
  | 'mean_center'
  | 'standardize'
  | 'binary_indicator'
  | 'ordinal_score'
  | 'treatment'

export interface VariableEncoding {
  method: VariableEncodingMethod
  referenceLevel?: string | null
  levels?: string[]
}

export interface ModelEdge {
  id: string
  from: string
  to: string
  kind: 'regression'
  label?: string
  hypothesis?: string
  estimand?: string
}

export interface ModelModeration {
  id: string
  moderatorNodeId: string
  secondaryModeratorNodeId?: string
  targetEdgeId: string
  productTermId: string
  moderatorProductTermId?: string
}

export interface ModelCovariateAssignment {
  nodeId: string
  outcomeNodeIds: string[]
}

export interface EstimandSpec {
  analysisRole:
    | 'preregistered_primary'
    | 'preregistered_secondary'
    | 'planned_not_preregistered'
    | 'exploratory_post_data'
  causalTarget: boolean
  identificationAssumptions: string[]
  effectScale:
    | 'mean_difference'
    | 'standardized_difference'
    | 'odds_ratio'
    | 'indirect_effect'
    | 'within_person_slope'
    | 'regression_coefficient'
}

export interface ModelSpec {
  schemaVersion: string
  modelId: string
  name: string
  description?: string
  datasetVersionId: string
  contextHash?: string | null
  sampleVersionId?: string | null
  sampleHash?: string | null
  structureVersionId?: string | null
  structureHash?: string | null
  measurementVersionId?: string | null
  measurementHash?: string | null
  datasetSha256?: string | null
  estimandSpec?: EstimandSpec | null
  design: {
    timeStructure: 'cross_sectional' | 'longitudinal' | 'experimental'
    clustering: 'none' | 'known_clustered'
    claimMode: 'associational' | 'causal_with_assumptions'
  }
  /** SEM measurement-only models may have no structural nodes or regression edges. */
  nodes: ModelNode[]
  edges: ModelEdge[]
  moderations: ModelModeration[]
  covariates: ModelCovariateAssignment[]
  latents?: Array<{
    id: string
    name: string
    level?: 'first_order' | 'higher_order'
    indicators: string[]
  }>
  estimation: {
    family: 'ols' | 'sem'
    estimator?: 'ML' | 'WLSMV'
    groupVariableId?: string | null
    invariance?: boolean
    multiGroup?: {
      compareStructuralPaths: boolean
      estimateLatentMeans: boolean
      partialInvarianceReleases?: Array<{
        stage: 'metric' | 'scalar' | 'strict'
        constraint: 'loading' | 'intercept_or_threshold' | 'residual'
        latentId: string | null
        indicatorId: string
        rationale: string
      }>
    }
    standardErrors: 'classical' | 'hc3' | 'standard' | 'robust' | 'bootstrap'
    confidenceLevel: number
    bootstrap: {
      enabled: boolean
      replicates: number
      method: 'percentile'
      seed: number
    }
    missing: 'complete_cases_per_model' | 'fiml'
    centering: { method: 'none' | 'mean'; nodeIds: string[] }
    reportScale: 'unstandardized_primary' | 'unstandardized_only'
  }
  canvas?: { positions?: Record<string, { x: number; y: number }> }
}

export interface ModelValidation {
  valid: boolean
  structuralStatus: 'valid' | 'invalid'
  errors: string[]
  warnings: Array<{ code: string; severity: 'warning'; message: string }>
  template: `model_${number}` | 'sem' | null
  catalogVersion: string
  matchStatus: 'exact' | 'custom' | 'sem' | 'invalid'
  processModelNumber: number | null
  displayName: string
  executionAvailable: boolean
  unsupportedReason: string | null
  sampleFlow: {
    original: number
    selected?: number
    included: number
    excluded: number
    missingRows?: number
    finalN?: number
    missingMethod: string
  } | null
}

export interface ModelDraftVersion {
  schemaVersion: string
  id: string
  status: 'draft'
  datasetId: string
  modelId: string
  updatedAt: string
  modelHash: string
  validation: ModelValidation
  modelSpec: ModelSpec
}

export interface FrozenModelVersion {
  schemaVersion: string
  id: string
  status: 'frozen'
  datasetId: string
  modelId: string
  version: number
  createdAt: string
  modelHash: string
  overrideReason: string | null
  validation: ModelValidation
  modelSpec: ModelSpec
}

export interface ModelVariable {
  id: string
  label: string
  kind: 'observed' | 'scale_score'
  dataType: 'continuous' | 'binary' | 'nominal' | 'ordinal'
  source: string
  encodingHint: VariableEncoding & { label: string; reason: string }
}
