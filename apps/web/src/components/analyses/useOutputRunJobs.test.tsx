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

beforeEach(() => {
  vi.clearAllMocks()
})

describe('useOutputRunJobs', () => {
  it('recovers an indexed run from the authoritative job endpoint', async () => {
    vi.mocked(getEmpiricalAnalysisJob).mockResolvedValue({
      id: 'run_1',
      status: 'succeeded',
    } as EmpiricalAnalysisJob)

    const { result } = renderHook(() => useOutputRunJobs(['run_1', 'run_1']), { wrapper })

    await waitFor(() => {
      expect(result.current.get('run_1')?.status).toBe('succeeded')
    })
    expect(getEmpiricalAnalysisJob).toHaveBeenCalledWith('run_1')
    expect(getEmpiricalAnalysisJob).toHaveBeenCalledTimes(1)
  })
})
