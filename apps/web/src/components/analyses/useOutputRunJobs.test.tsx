import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getEmpiricalAnalysisJob } from '../../api'
import type { EmpiricalAnalysisJob } from '../../types'
import { useOutputRunJobs } from './useOutputRunJobs'

vi.mock('../../api', () => ({
  getEmpiricalAnalysisJob: vi.fn(),
}))

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

function recoveredJob(datasetId = 'dataset_demo'): EmpiricalAnalysisJob {
  return {
    id: 'run_1',
    datasetId,
    measurementVersion: null,
    status: 'succeeded',
  } as EmpiricalAnalysisJob
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useOutputRunJobs', () => {
  it('recovers an indexed run from the authoritative job endpoint', async () => {
    vi.mocked(getEmpiricalAnalysisJob).mockResolvedValue(recoveredJob())

    const { result } = renderHook(
      () => useOutputRunJobs(['run_1', 'run_1'], 'dataset_demo', null),
      { wrapper },
    )

    await waitFor(() => {
      expect(result.current.get('run_1')?.status).toBe('succeeded')
    })
    expect(getEmpiricalAnalysisJob).toHaveBeenCalledWith('run_1', expect.any(AbortSignal))
    expect(getEmpiricalAnalysisJob).toHaveBeenCalledTimes(1)
  })

  it('does not bind a server job that belongs to another dataset', async () => {
    vi.mocked(getEmpiricalAnalysisJob).mockResolvedValue(recoveredJob('dataset_other'))

    const { result } = renderHook(
      () => useOutputRunJobs(['run_1'], 'dataset_demo', null),
      { wrapper },
    )

    await waitFor(() => expect(getEmpiricalAnalysisJob).toHaveBeenCalledWith('run_1', expect.any(AbortSignal)))
    expect(result.current.has('run_1')).toBe(false)
  })

  it('aborts an in-flight recovery request when the Output query unmounts', async () => {
    let observedSignal: AbortSignal | undefined
    vi.mocked(getEmpiricalAnalysisJob).mockImplementation((_runId, signal) => {
      observedSignal = signal
      return new Promise<EmpiricalAnalysisJob>(() => {})
    })

    const { unmount } = renderHook(
      () => useOutputRunJobs(['run_1'], 'dataset_demo', null),
      { wrapper },
    )

    await waitFor(() => expect(observedSignal).toBeDefined())
    expect(observedSignal?.aborted).toBe(false)
    unmount()
    expect(observedSignal?.aborted).toBe(true)
  })
})
