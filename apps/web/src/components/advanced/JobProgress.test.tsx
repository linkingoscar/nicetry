import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { JobProgress } from './JobProgress'
import * as advancedApi from '../../api/advanced'
import type { AdvancedAnalysisCapability } from '../../types'
import type { AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'

vi.mock('../../api/advanced')

describe('JobProgress', () => {
  const capability: AdvancedAnalysisCapability = {
    family: 'power_analysis',
    label: '功效分析',
    status: 'experimental',
    executionAvailable: true,
    specVersion: '0.1.0',
    resultVersion: '0.1.0',
    plannedEngine: 'R',
    minimumValidation: [],
    slices: [{ id: 'power_analysis.analytic.regression', label: '回归解析功效', status: 'experimental', executionAvailable: true, supportBoundary: 'test' }]
  }

  const initialJob: AdvancedJobResponse = {
    id: 'job-123',
    status: 'running',
    stage: 'validate_spec',
    progress: 0.1,
    analysisId: 'test',
    family: 'power_analysis',
    specHash: 'hash',
    cancelRequested: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  }

  beforeEach(() => {
    vi.resetAllMocks()
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  it('polls job status and calls onComplete when succeeded', async () => {
    const mockResult: AdvancedResultResponse = {
      schemaVersion: '0.1.0',
      apaReports: [],
      plots: [],
      run: { status: 'succeeded' },
    }

    let pollCount = 0
    vi.mocked(advancedApi.getAdvancedAnalysisStatus).mockImplementation(async () => {
      pollCount++
      if (pollCount === 1) return initialJob
      return { ...initialJob, status: 'succeeded' }
    })

    vi.mocked(advancedApi.getAdvancedAnalysisResult).mockResolvedValue(mockResult)

    const onComplete = vi.fn()
    render(
      <JobProgress
        jobId="job-123"
        initialJob={initialJob}
        capability={capability}
        onComplete={onComplete}
        onCancel={vi.fn()}
      />
    )

    // Run the timer forward to trigger the fetchStatus call
    await vi.runOnlyPendingTimersAsync()
    await vi.runOnlyPendingTimersAsync()

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledWith(
        expect.objectContaining({ status: 'succeeded' }),
        mockResult
      )
    })
  })

  it('calls cancel API when cancel button is clicked', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisStatus).mockResolvedValue(initialJob)
    vi.mocked(advancedApi.cancelAdvancedAnalysis).mockResolvedValue({ ...initialJob, status: 'cancelling' })

    render(
      <JobProgress
        jobId="job-123"
        initialJob={initialJob}
        capability={capability}
        onComplete={vi.fn()}
        onCancel={vi.fn()}
      />
    )

    const cancelBtn = screen.getByRole('button', { name: '取消分析' })
    fireEvent.click(cancelBtn)

    expect(advancedApi.cancelAdvancedAnalysis).toHaveBeenCalledWith('job-123')
    expect(screen.getByText('正在取消...')).toBeInTheDocument()
  })

  it('shows a persisted failure code and actionable remediation', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisStatus).mockResolvedValue({
      ...initialJob,
      status: 'failed',
      stage: 'failed',
      error: '问卷测量的完整案例少于 20',
      errorCode: 'MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS',
      remediation: '检查题项缺失和编码；先处理缺失或补充样本。',
    })

    render(
      <JobProgress
        jobId="job-123"
        initialJob={initialJob}
        capability={capability}
        onComplete={vi.fn()}
        onCancel={vi.fn()}
      />
    )

    await vi.runOnlyPendingTimersAsync()
    expect(await screen.findByText('MEASUREMENT_INSUFFICIENT_COMPLETE_OBSERVATIONS')).toBeInTheDocument()
    expect(screen.getByText(/先处理缺失或补充样本/)).toBeInTheDocument()
  })
})
