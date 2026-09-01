import type { EmpiricalAnalysisSegmentMap } from '../../types'

export interface SegmentQueryState<Data> {
  data: Data | null | undefined
  isLoading: boolean
  isError: boolean
  error: unknown
}

export interface EmpiricalResultQueries {
  summary: SegmentQueryState<EmpiricalAnalysisSegmentMap['summary']>
  correlation: SegmentQueryState<EmpiricalAnalysisSegmentMap['correlation']>
  efaCfa: SegmentQueryState<EmpiricalAnalysisSegmentMap['efa_cfa']>
  validity: SegmentQueryState<EmpiricalAnalysisSegmentMap['validity']>
  regression: SegmentQueryState<EmpiricalAnalysisSegmentMap['regression']>
}
