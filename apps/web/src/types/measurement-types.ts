export type ScaleAggregation = 'mean' | 'sum'

export interface ConstructDraft {
  id: string
  name: string
  itemIds: string[]
  reverseItemIds: string[]
  theoreticalMinimum: number
  theoreticalMaximum: number
  aggregation: ScaleAggregation
  minimumValidProportion: number
}

export interface ConstructDefinition extends ConstructDraft {
  minimumValidItems: number
  outputVariableId: string
}

export interface ItemAnalysis {
  itemId: string
  label: string
  reversed: boolean
  validCount: number
  missingCount: number
  mean: number | null
  standardDeviation: number | null
  floorRate: number | null
  ceilingRate: number | null
  correctedItemTotalCorrelation: number | null
  alphaIfDeleted: number | null
  omegaIfDeleted: number | null
}

export interface MeasurementReport {
  constructId: string
  outputVariableId: string
  completeCaseCount: number
  alpha: number | null
  omega: number | null
  ordinalAlpha?: number | null
  ordinalOmega?: number | null
  structurallyMissingCount?: number | null
  itemAnalysis: ItemAnalysis[]
  scoreDistribution: {
    validCount: number
    missingCount: number
    mean: number | null
    standardDeviation: number | null
    minimum: number | null
    q1: number | null
    median: number | null
    q3: number | null
    maximum: number | null
  }
}

export interface MeasurementVersion {
  schemaVersion: string
  id: string
  datasetVersionId: string
  version: number
  createdAt: string
  changeNote: string | null
  status: 'ready_for_model_canvas'
  constructs: ConstructDefinition[]
  reports: MeasurementReport[]
  derivedDataset: {
    id: string
    sourceDatasetVersionId: string
    measurementVersion: number
    storage: string
    sha256: string
    rowCount: number
    columnCount: number
    scoreVariables: Array<{ id: string; label: string; type: 'scale_score' }>
  }
  transformationPreview: Array<Record<string, number | null>>
  transformationLog: Array<{ constructId: string; message: string }>
  warnings: Array<{ code: string; severity: 'warning'; message: string }>
}
