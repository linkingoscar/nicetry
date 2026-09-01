import { useQuery } from '@tanstack/react-query'

import { getApplicableCapabilities } from '../api/analysis-context'
import type { ResolvedAnalysisContext } from '../types/analysis-context'

export function useApplicableCapabilities(context: ResolvedAnalysisContext | null | undefined) {
  const structureRevision = context?.structure?.revision ?? null
  const studyRevision = context?.studyContext?.revision ?? null
  return useQuery({
    queryKey: [
      'applicable-capabilities',
      context?.dataset.id ?? null,
      context?.contextHash ?? null,
      structureRevision,
      studyRevision,
      context?.measurement?.id ?? null,
      context?.sample?.id ?? null,
    ],
    queryFn: ({ signal }) =>
      getApplicableCapabilities(context?.dataset.id as string, context?.contextHash as string, signal),
    enabled: Boolean(context?.dataset.id && context?.contextHash),
    retry: false,
  })
}
