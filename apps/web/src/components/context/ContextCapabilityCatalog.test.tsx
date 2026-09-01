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
            sliceId: 'multilevel_model.gaussian.two_level',
            label: '两层 Gaussian LMM',
            applicable: false,
            blockedReason: 'clusterId',
            missingRequirements: ['clusterId'],
          }),
          capability({
            family: 'multiple_imputation',
            sliceId: 'multiple_imputation.mice_dataset_generation',
            label: 'MICE generation',
            productVisible: false,
          }),
          capability({ sliceId: 'future.unavailable', label: '不可执行方法', executionAvailable: false }),
        ],
      },
      isLoading: false,
      error: null,
    } as ReturnType<typeof useApplicableCapabilities>)
    vi.mocked(createAnalysisDraft).mockResolvedValue({ id: 'draft_demo' } as never)
    vi.mocked(getAnalysisDraftValidity).mockResolvedValue({ validity: 'ready' } as never)
  })

  it('renders only applicable executable product methods and keeps blocked reasons inspectable', async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ContextCapabilityCatalog context={context} />
      </QueryClientProvider>,
    )

    expect(screen.getByText('组间 ANOVA')).toBeInTheDocument()
    expect(screen.getByText('已验证')).toBeInTheDocument()
    expect(screen.getByText('有条件：仍需论文证据图')).toBeInTheDocument()
    expect(screen.getByText(/查看 1 个当前不可用的方法/)).toBeInTheDocument()
    expect(screen.queryByText('MICE generation')).not.toBeInTheDocument()
    expect(screen.queryByText(/不可执行方法/)).not.toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: '配置组间 ANOVA' }))
    await waitFor(() => {
      expect(createAnalysisDraft).toHaveBeenCalledWith('dataset_demo', {
        sliceId: 'experimental_design.factorial_anova.long.single_outcome',
        contextHash: context.contextHash,
      })
    })
  })

  it('routes built-in empirical and model capabilities without creating an advanced draft', async () => {
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

    await userEvent.setup().click(screen.getByRole('button', { name: '配置结构方程模型' }))
    expect(onNavigate).toHaveBeenCalledWith(expect.objectContaining({ view: 'model', sliceId: 'model.sem' }))
    expect(createAnalysisDraft).not.toHaveBeenCalled()
  })

  it('filters without exposing unavailable methods and restores the list when filters clear', async () => {
    render(<QueryClientProvider client={new QueryClient()}><ContextCapabilityCatalog context={context} /></QueryClientProvider>)
    expect(screen.getByText(context.contextHash)).not.toBeVisible()
    await userEvent.type(screen.getByRole('searchbox', { name: '搜索方法' }), 'anova')
    expect(screen.getByRole('button', { name: '配置组间 ANOVA' })).toBeVisible()
    await userEvent.clear(screen.getByRole('searchbox', { name: '搜索方法' }))
    await userEvent.type(screen.getByRole('searchbox', { name: '搜索方法' }), 'MICE')
    expect(screen.queryByRole('button', { name: /配置/ })).not.toBeInTheDocument()
    expect(screen.getByText(/没有匹配的方法/)).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: '清除筛选' }))
    expect(screen.getByRole('button', { name: '配置组间 ANOVA' })).toBeVisible()
  })

  it('leaves a failed draft recoverable instead of silently doing nothing', async () => {
    vi.mocked(createAnalysisDraft).mockRejectedValueOnce(new Error('数据版本已更新'))
    render(<QueryClientProvider client={new QueryClient()}><ContextCapabilityCatalog context={context} /></QueryClientProvider>)
    await userEvent.click(screen.getByRole('button', { name: '配置组间 ANOVA' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('数据版本已更新')
    expect(screen.getByRole('button', { name: '配置组间 ANOVA' })).toBeEnabled()
  })
})
