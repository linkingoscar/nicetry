import { useQueries } from '@tanstack/react-query'

import { getEmpiricalAnalysisJob } from '../../api'
import type { EmpiricalAnalysisJob } from '../../types'

const TERMINAL_STATUSES = new Set(['succeeded', 'failed', 'cancelled'])
const MAX_RECOVERED_RUNS = 30

export function useOutputRunJobs(
  runIds: string[],
  datasetId: string,
  measurementVersion: number | null,
): Map<string, EmpiricalAnalysisJob> {
  const uniqueRunIds = [...new Set(runIds)].slice(0, MAX_RECOVERED_RUNS)
  const queries = useQueries({
    queries: uniqueRunIds.map((runId) => ({
      queryKey: ['empirical-analysis-job', runId],
      queryFn: ({ signal }: { signal: AbortSignal }) => getEmpiricalAnalysisJob(runId, signal),
      retry: false,
      staleTime: 2_000,
      refetchInterval: (query: { state: { data?: EmpiricalAnalysisJob; status: string } }) => {
        if (query.state.status === 'error') return false
        const status = query.state.data?.status
        return status && TERMINAL_STATUSES.has(status) ? false : 1_000
      },
    })),
  })

  const jobs = new Map<string, EmpiricalAnalysisJob>()
  queries.forEach((query, index) => {
    const job = query.data
    if (job?.datasetId === datasetId && job.measurementVersion === measurementVersion) {
      jobs.set(uniqueRunIds[index], job)
    }
  })
  return jobs
}
