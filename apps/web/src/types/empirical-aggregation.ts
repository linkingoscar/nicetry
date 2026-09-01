export interface EmpiricalAggregationDiagnostic {
  id: string
  label: string
  available: boolean
  reasonCode?: string
  reason?: string
  observations?: number
  clusterCount?: number
  eligibleRwgClusterCount?: number
  minimumClusterSize?: number
  maximumClusterSize?: number
  averageClusterSize?: number | null
  icc1?: number | null
  icc2?: number | null
  designEffect?: number | null
  rwg?: {
    nullDistribution: string
    itemCount: number
    scoreAggregation: string
    expectedScoreVariance: number | null
    mean: number | null
    median: number | null
    proportionAtLeastPoint70: number | null
    byCluster: number[]
  }
  interpretation?: string
}
