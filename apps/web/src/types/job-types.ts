import type { ResultBundle } from './result-bundle-types'

export type AnalysisJobStatus =
  | 'queued'
  | 'running'
  | 'cancelling'
  | 'succeeded'
  | 'failed'
  | 'cancelled'

export interface AnalysisJob {
  id: string
  jobKind?: 'model' | 'empirical'
  datasetId: string
  modelId: string
  modelVersion: number
  modelVersionId: string
  status: AnalysisJobStatus
  stage: string
  progress: number
  completedReplicates: number
  totalReplicates: number
  cancelRequested: boolean
  createdAt: string
  updatedAt: string
  error: string | null
  result: ResultBundle | null
  resultPath?: string | null
}
