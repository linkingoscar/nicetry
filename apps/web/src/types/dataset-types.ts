export type VariableType =
  | 'continuous'
  | 'binary'
  | 'nominal'
  | 'ordinal'
  | 'likert'
  | 'id'
  | 'text'

export interface DatasetVariable {
  id: string
  originalName: string
  label: string
  storageType: string
  inferredType: VariableType
  confirmedType: VariableType | null
  confidence: number
  rationale: string
  missingCount: number
  missingRate: number
  uniqueCount: number
  sampleValues: Array<string | number | boolean | null>
  valueLabels: Record<string, string | number | boolean>
  issues: string[]
  minimum?: number
  maximum?: number
}

export interface DatasetVersion {
  schemaVersion: string
  id: string
  projectId: string
  createdAt: string
  originalFile: {
    name: string
    format: 'csv' | 'xlsx' | 'sav' | 'dta' | 'por'
    sizeBytes: number
    sha256: string
    encoding?: string
    delimiter?: string
    sheet?: string
    sheetNames?: string[]
  }
  storage: { raw: string; normalized: string }
  rowCount: number
  columnCount: number
  variables: DatasetVariable[]
  preview: Array<Record<string, string | number | boolean | null>>
  warnings: Array<{ code: string; severity: 'warning'; message: string }>
  dictionary: {
    version: number
    confirmedCount: number
    totalCount: number
    status: 'draft' | 'confirmed'
  }
}
