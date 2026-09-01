import { useQuery } from '@tanstack/react-query'

import { getResolvedAnalysisContext } from '../api/analysis-context'

export function useResolvedAnalysisContext(
  datasetId: string | null,
  measurementVersion?: number | null,
) {
  return useQuery({
    queryKey: ['resolved-analysis-context', datasetId, measurementVersion ?? null, null, null],
    queryFn: ({ signal }) =>
      getResolvedAnalysisContext({ datasetId: datasetId as string, measurementVersion }, signal),
    enabled: Boolean(datasetId),
    retry: false,
  })
}
