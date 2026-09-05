import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createImputationPlan, runImputationPlan } from '../../api/imputation-plans'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { registerOutputRun } from '../analyses/outputRunRegistry'
import { ImputationPlanWorkspace } from './ImputationPlanWorkspace'

vi.mock('../../api/imputation-plans', async () => {
  const actual = await vi.importActual<typeof import('../../api/imputation-plans')>('../../api/imputation-plans')
  return {
    ...actual,
    createImputationPlan: vi.fn(),
    runImputationPlan: vi.fn(),
  }
})
vi.mock('../analyses/outputRunRegistry', () => ({ registerOutputRun: vi.fn() }))
vi.mock('../advanced/JobProgress', () => ({
  JobProgress: ({ jobId }: { jobId: string }) => <div>运行 {jobId}</div>,
}))

const context = {
  projectId: 'project_demo',
  dataset: { id: 'dataset_v1', hash: 'a'.repeat(64), rowCount: 100 },
  sample: { id: 'sample_all', hash: 'b'.repeat(64), kind: 'virtual' },
  measurement: null,
  structure: null,
  studyContext: {
    value: {
      design: 'observational',
      timeStructure: 'cross_sectional',
      dependenceStructure: 'independent',
    },
  },
  contextHash: 'c'.repeat(64),
} as unknown as ResolvedAnalysisContext

const variables = [
  { id: 'y', name: 'y', label: 'Y', type: 'numeric' as const, missingRate: 0.1, levels: [] },
  { id: 'x1', name: 'x1', label: 'X1', type: 'numeric' as const, missingRate: 0.05, levels: [] },
  { id: 'x2', name: 'x2', label: 'X2', type: 'numeric' as const, missingRate: 0, levels: [] },
]

describe('ImputationPlanWorkspace Output registration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(createImputationPlan).mockResolvedValue({
      id: 'mi_plan_1',
      datasetVersionId: 'dataset_v1',
      datasetSha256: 'd'.repeat(64),
      sampleHash: 'e'.repeat(64),
      structureHash: 'f'.repeat(64),
      measurementHash: null,
      predictorMatrixHash: '1'.repeat(64),
    } as never)
    vi.mocked(runImputationPlan).mockResolvedValue({
      planVersionId: 'mi_plan_1',
      imputationPlanVersionId: 'mi_plan_1',
      imputationDatasetVersionId: 'dataset_mi_1',
      contextHash: context.contextHash,
      job: {
        id: 'advanced_job_mi_1',
        status: 'queued',
        createdAt: '2026-09-04T12:00:00Z',
      },
    } as never)
  })

  it('registers the authoritative MI job reference in the project Output index after submission', async () => {
    const user = userEvent.setup()
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ImputationPlanWorkspace context={context} variables={variables} />
      </QueryClientProvider>,
    )

    await user.click(screen.getByRole('button', { name: '检查并保存插补设置' }))
    expect(await screen.findByRole('button', { name: '运行多重插补与 Rubin 合并' })).toBeEnabled()

    await user.click(screen.getByRole('button', { name: '运行多重插补与 Rubin 合并' }))

    await waitFor(() => {
      expect(registerOutputRun).toHaveBeenCalledWith({
        runId: 'advanced_job_mi_1',
        projectId: 'project_demo',
        datasetVersionId: 'dataset_v1',
        measurementVersionId: null,
        source: 'advanced',
        label: '多重插补与 Rubin 合并',
        methodId: 'missing.multiple-imputation',
        family: 'multiple_imputation',
        createdAt: '2026-09-04T12:00:00Z',
      })
    })
    expect(await screen.findByText('运行 advanced_job_mi_1')).toBeInTheDocument()
  })
})
