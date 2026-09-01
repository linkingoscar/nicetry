import type { DatasetVersion } from './dataset-types'

export interface DatasetMergeReport {
  matchedCount: number
  primaryOnlyCount: number
  targetOnlyCount: number
  primaryDuplicates: number
  targetDuplicates: number
  warnings: string[]
}

export interface DatasetMergeResponse {
  dataset: DatasetVersion
  report: DatasetMergeReport
}
