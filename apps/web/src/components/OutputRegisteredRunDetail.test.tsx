import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getAnalysisJob, getAnalysisResult } from '../api/analyses'
import { getAdvancedAnalysisResult, getAdvancedAnalysisStatus } from '../api/advanced'
import type { RegisteredOutputRun } from './analyses/outputRunRegistry'
import { OutputRegisteredRunDetail } from './OutputRegisteredRunDetail'

vi.mock('../api/analyses', () => ({
  getAnalysisJob: vi.fn(),
  getAnalysisResult: vi.fn(),
}))
vi.mock('../api/advanced', () => ({
  getAdvancedAnalysisStatus: vi.fn(),
  getAdvancedAnalysisResult: vi.fn(),
}))
vi.mock('./ResultPanel', () => ({ ResultPanel: ({ title }: { title: string }) => <div>model-result:{title}</div> }))
vi.mock('./OutputAdvancedResultPreview', () => ({ OutputAdvancedResultPreview: ({ label }: { label: string }) => <div>advanced-result:{label}</div> }))

function renderDetail(run: RegisteredOutputRun) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <OutputRegisteredRunDetail run={run} onClose={vi.fn()} />
    </QueryClientProvider>,
  )
}

const baseRun = {
  projectId: 'project_demo',
  datasetVersionId: 'dataset_demo',
  measurementVersionId: null,
  createdAt: '2026-09-03T10:00:00Z',
} as const

beforeEach(() => vi.clearAllMocks())

describe('OutputRegisteredRunDetail', () => {
  it('recovers a model job first and loads its immutable result only after success', async () => {
    vi.mocked(getAnalysisJob).mockResolvedValue({ id: 'run_model', status: 'succeeded', error: null } as never)
    vi.mocked(getAnalysisResult).mockResolvedValue({ run: { id: 'run_model' } } as never)

    renderDetail({
      ...baseRun,
      runId: 'run_model',
      source: 'model',
      label: '简单中介',
      methodId: 'model.process',
      modelId: 'model_demo',
    })

    await waitFor(() => expect(getAnalysisJob).toHaveBeenCalledWith('run_model'))
    await waitFor(() => expect(getAnalysisResult).toHaveBeenCalledWith('run_model'))
    expect(await screen.findByText('model-result:简单中介 · 本次结果')).toBeInTheDocument()
    expect(getAdvancedAnalysisStatus).not.toHaveBeenCalled()
  })

  it('uses the advanced status/result endpoints for an advanced run', async () => {
    vi.mocked(getAdvancedAnalysisStatus).mockResolvedValue({ id: 'run_anova', status: 'succeeded', error: null } as never)
    vi.mocked(getAdvancedAnalysisResult).mockResolvedValue({ familyResult: { family: 'experimental_design' } } as never)

    renderDetail({
      ...baseRun,
      runId: 'run_anova',
      source: 'advanced',
      label: '组间析因方差分析',
      methodId: 'experimental_design.factorial_anova.long.single_outcome',
      family: 'experimental_design',
    })

    await waitFor(() => expect(getAdvancedAnalysisStatus).toHaveBeenCalled())
    await waitFor(() => expect(getAdvancedAnalysisResult).toHaveBeenCalled())
    expect(await screen.findByText('advanced-result:组间析因方差分析')).toBeInTheDocument()
    expect(getAnalysisJob).not.toHaveBeenCalled()
  })

  it('does not request a result while the server job is still running', async () => {
    vi.mocked(getAnalysisJob).mockResolvedValue({ id: 'run_running', status: 'running', error: null } as never)

    renderDetail({
      ...baseRun,
      runId: 'run_running',
      source: 'model',
      label: 'SEM',
      methodId: 'model.sem',
      modelId: 'model_sem',
    })

    expect(await screen.findByText(/运行中/)).toBeInTheDocument()
    expect(getAnalysisResult).not.toHaveBeenCalled()
  })
})
