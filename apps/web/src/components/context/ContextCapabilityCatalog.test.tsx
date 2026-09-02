import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createAnalysisDraft, getAnalysisDraftValidity } from '../../api/analysis-context'
import { useApplicableCapabilities } from '../../hooks/useApplicableCapabilities'
import type { ApplicableCapability, ResolvedAnalysisContext } from '../../types/analysis-context'
import { ContextCapabilityCatalog } from './ContextCapabilityCatalog'

vi.mock('../../api/analysis-context', async () => {
  const actual = await vi.importActual<typeof import('../../api/analysis-context')>('../../api/analysis-context')
  return { ...actual, createAnalysisDraft: vi.fn(), getAnalysisDraftValidity: vi.fn() }
})
vi.mock('../../hooks/useApplicableCapabilities')

const context = {
  schemaVersion: '1.0.0',
  projectId: 'project_demo',
  dataset: { id: 'dataset_demo', hash: 'a'.repeat(64), rowCount: 10 },
  studyContext: null,
  structure: null,
  measurement: null,
  sample: { id: 'sample_all_demo', hash: 'b'.repeat(64), kind: 'virtual' },
  imputation: null,
  contextHash: 'c'.repeat(64),
  validity: 'ready',
  missingRequirements: [],
  warnings: [],
} as unknown as ResolvedAnalysisContext

function capability(overrides: Partial<ApplicableCapability>): ApplicableCapability {
  return {
    family: 'experimental_design',
    sliceId: 'experimental_design.factorial_anova.long.single_outcome',
    label: '组间 ANOVA',
    status: 'supported',
    executionAvailable: true,
    maturityLevel: 'validated',
    validationLevel: 'internally_validated',
    publicationEligibility: 'conditional',
    publicationEligibilityReason: '需要绑定论文级证据图。',
    validationEvidence: {
      contractTests: true,
      applicabilityTests: true,
      failureFixtures: true,
      externalOracle: null,
      numericGoldenId: null,
    },
    applicable: true,
    requiresRevalidation: true,
    productVisible: true,
    requiredRoles: [],
    optionalRoles: [],
    requiredArtifacts: ['dataset'],
    defaultBindings: {},
    missingRequirements: [],
    blockedReason: null,
    supportBoundary: 'test',
    ...overrides,
  }
}

describe('ContextCapabilityCatalog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useApplicableCapabilities).mockReturnValue({
      data: {
        schemaVersion: '1.0.0',
        contextHash: context.contextHash,
        capabilities: [
          capability({}),
          capability({
            family: 'multilevel_model',
            sliceId: 'multilevel_model.gaussian.two_level',
            label: '两层 Gaussian LMM',
            applicable: false,
            blockedReason: '需要先指定 clusterId。',
            missingRequirements: ['clusterId'],
          }),
          capability({
            family: 'multiple_imputation',
            sliceId: 'multiple_imputation.mice_dataset_generation',
            label: 'MICE generation',
            productVisible: false,
          }),
          capability({
            family: 'power_analysis',
            sliceId: 'power_analysis.analytic.t_test',
            label: 't test power',
            executionAvailable: false,
            applicable: false,
            blockedReason: '当前版本未开放执行。',
          }),
        ],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useApplicableCapabilities>)
    vi.mocked(createAnalysisDraft).mockResolvedValue({ id: 'draft_demo' } as never)
    vi.mocked(getAnalysisDraftValidity).mockResolvedValue({ validity: 'ready' } as never)
  })

  it('keeps blocked and unavailable product methods visible while hiding internal consumers', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ContextCapabilityCatalog context={context} />
      </QueryClientProvider>,
    )

    expect(screen.getByText('组间析因方差分析')).toBeInTheDocument()
    expect(screen.getByText('两层 Gaussian LMM')).toBeInTheDocument()
    expect(screen.getByText('需要补充设置')).toBeInTheDocument()
    expect(screen.getByText('t 检验解析功效')).toBeInTheDocument()
    expect(screen.getByText('当前不可运行')).toBeInTheDocument()
    expect(screen.getAllByText('实验性').length).toBeGreaterThan(0)
    expect(screen.queryByText('MICE generation')).not.toBeInTheDocument()
    expect(screen.queryByText('有条件：仍需论文证据图')).not.toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: '配置组间析因方差分析' }))
    await waitFor(() => {
      expect(createAnalysisDraft).toHaveBeenCalledWith('dataset_demo', {
        sliceId: 'experimental_design.factorial_anova.long.single_outcome',
        contextHash: context.contextHash,
      })
    })
  })

  it('routes built-in empirical and model capabilities through registry adapters without creating an advanced draft', async () => {
    const onNavigate = vi.fn()
    vi.mocked(useApplicableCapabilities).mockReturnValue({
      data: {
        schemaVersion: '1.0.0',
        contextHash: context.contextHash,
        capabilities: [
          capability({ family: 'model', sliceId: 'model.sem', label: '结构方程模型' }),
        ],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useApplicableCapabilities>)

    render(
      <QueryClientProvider client={new QueryClient()}>
        <ContextCapabilityCatalog context={context} onNavigate={onNavigate} />
      </QueryClientProvider>,
    )

    await userEvent.setup().click(screen.getByRole('button', { name: '配置结构方程模型（SEM）' }))
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ view: 'model', sliceId: 'model.sem' }))
    expect(createAnalysisDraft).not.toHaveBeenCalled()
  })

  it('searches aliases and blocked methods, filters readiness, and restores the list when filters clear', async () => {
    const user = userEvent.setup()
    render(<QueryClientProvider client={new QueryClient()}><ContextCapabilityCatalog context={context} /></QueryClientProvider>)
    expect(screen.getByText(context.contextHash)).not.toBeVisible()

    await user.type(screen.getByRole('searchbox', { name: '搜索方法' }), 'factorial ANOVA')
    expect(screen.getByRole('button', { name: '配置组间析因方差分析' })).toBeVisible()

    await user.clear(screen.getByRole('searchbox', { name: '搜索方法' }))
    await user.type(screen.getByRole('searchbox', { name: '搜索方法' }), 'LMM')
    expect(screen.getByText('两层 Gaussian LMM')).toBeVisible()
    expect(screen.getByText('需要先指定 clusterId。')).toBeVisible()

    await user.clear(screen.getByRole('searchbox', { name: '搜索方法' }))
    await user.selectOptions(screen.getByRole('combobox', { name: '当前状态' }), 'needs-setup')
    expect(screen.getByText('两层 Gaussian LMM')).toBeVisible()
    expect(screen.queryByText('组间析因方差分析')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '清除筛选' }))
    expect(screen.getByRole('button', { name: '配置组间析因方差分析' })).toBeVisible()
  })

  it('leaves a failed draft recoverable instead of silently doing nothing', async () => {
    vi.mocked(createAnalysisDraft).mockRejectedValueOnce(new Error('数据版本已更新'))
    render(<QueryClientProvider client={new QueryClient()}><ContextCapabilityCatalog context={context} /></QueryClientProvider>)
    await userEvent.click(screen.getByRole('button', { name: '配置组间析因方差分析' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('数据版本已更新')
    expect(screen.getByRole('button', { name: '配置组间析因方差分析' })).toBeEnabled()
  })
})
