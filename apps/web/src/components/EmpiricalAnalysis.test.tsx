import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listAnalysisSamples, runEmpiricalAnalysis } from '../api'
import { getResolvedAnalysisContext } from '../api/analysis-context'
import type { DatasetVersion, MeasurementVersion } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import type { EmpiricalProcedure } from '../types/empirical-types'
import type { AnalysisParadigm } from '../types/study-context'
import { EmpiricalAnalysis } from './EmpiricalAnalysis'
import { empiricalProcedures } from './empirical/empiricalProcedures'


vi.mock('../api', () => ({
  runEmpiricalAnalysis: vi.fn(() => new Promise(() => undefined)),
  listAnalysisSamples: vi.fn(async () => []),
  empiricalAnalysisExportUrl: vi.fn(() => '/export.xlsx'),
}))

vi.mock('../hooks/useApplicableCapabilities', () => ({
  useApplicableCapabilities: () => ({ data: { capabilities: empiricalProcedures.map((p) => ({ sliceId: p.slice, applicable: true, executionAvailable: true, productVisible: true })) }, isLoading: false, isError: false }),
}))
vi.mock('../hooks/useJobProgress', () => ({ useJobProgress: vi.fn() }))
vi.mock('../api/analysis-context', () => ({ getResolvedAnalysisContext: vi.fn() }))

const variable = (
  id: string,
  originalName: string,
  confirmedType: 'continuous' | 'binary' | 'likert' | 'id',
) => ({
  id,
  originalName,
  label: originalName,
  storageType: 'float64',
  inferredType: confirmedType,
  confirmedType,
  confidence: 1,
  rationale: 'test',
  missingCount: 0,
  missingRate: 0,
  uniqueCount: 5,
  sampleValues: [1, 2],
  valueLabels: {},
  issues: [],
})

const dataset = {
  id: 'dataset_1234567890abcdef',
  variables: [
    variable('var_1_aaaaaaaa', 'x1', 'likert'),
    variable('var_2_bbbbbbbb', 'x2', 'likert'),
    variable('var_3_cccccccc', 'y1', 'likert'),
    variable('var_4_dddddddd', 'y2', 'likert'),
    variable('var_5_eeeeeeee', 'group', 'binary'),
    variable('var_6_ffffffff', 'age', 'continuous'),
    variable('var_7_gggggggg', 'team_id', 'id'),
  ],
} as unknown as DatasetVersion

const measurement = {
  version: 1,
  constructs: [
    { id: 'construct_x', name: '自变量', itemIds: ['var_1_aaaaaaaa', 'var_2_bbbbbbbb'] },
    { id: 'construct_y', name: '结果变量', itemIds: ['var_3_cccccccc', 'var_4_dddddddd'] },
  ],
  derivedDataset: {
    rowCount: 120,
    scoreVariables: [
      { id: 'scale_x', label: '自变量', type: 'scale_score' },
      { id: 'scale_y', label: '结果变量', type: 'scale_score' },
    ],
  },
} as unknown as MeasurementVersion

function renderCenter({
  analysisContext,
  researchParadigm = 'questionnaire',
  analysisProcedure = 'descriptives',
}: {
  analysisContext?: ResolvedAnalysisContext
  researchParadigm?: AnalysisParadigm
  analysisProcedure?: EmpiricalProcedure
} = {}) {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <EmpiricalAnalysis
        dataset={dataset}
        measurement={measurement}
        analysisContext={analysisContext}
        researchParadigm={researchParadigm}
        analysisProcedure={analysisProcedure}
      />
    </QueryClientProvider>,
  )
}

describe('EmpiricalAnalysis single procedures', () => {
  beforeEach(() => {
    vi.mocked(runEmpiricalAnalysis).mockClear()
    vi.mocked(listAnalysisSamples).mockResolvedValue([])
    vi.mocked(getResolvedAnalysisContext).mockReset()
    localStorage.clear()
  })

  it('requires selected variables and runs descriptives without other analyses', async () => {
    renderCenter()
    expect(screen.getByRole('button', { name: '运行描述统计' })).toBeDisabled()
    expect(screen.queryByLabelText('因变量（Y）')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: '自变量' }))
    fireEvent.click(screen.getByRole('button', { name: '运行描述统计' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2]).toMatchObject({
      procedure: 'descriptives', analysisVariableIds: ['scale_x'], constructIds: [],
      outcomeVariableId: null, predictorVariableIds: [], groupVariableId: null,
      longitudinalPanel: null, diaryMultilevel: null,
    })
  })

  it('renders the requested correlation method without a page-local switcher and submits only its choices', async () => {
    renderCenter({ analysisProcedure: 'correlation' })
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: '描述统计' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('EFA 旋转方法')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: '自变量' }))
    fireEvent.click(screen.getByRole('checkbox', { name: '结果变量' }))
    fireEvent.click(screen.getByRole('button', { name: '运行相关分析' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2]).toMatchObject({ procedure: 'correlation', analysisVariableIds: ['scale_x', 'scale_y'], outcomeVariableId: null, predictorVariableIds: [], constructIds: [] })
  })

  it('keeps EFA and CFA as independent method routes', () => {
    const efaView = renderCenter({ analysisProcedure: 'efa' })
    expect(screen.getByLabelText('EFA 旋转方法')).toBeInTheDocument()
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()

    efaView.unmount()
    renderCenter({ analysisProcedure: 'cfa' })
    expect(screen.queryByLabelText('EFA 旋转方法')).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: '自变量（2 题）' })).toBeInTheDocument()
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()
  })

  it('restores unsubmitted method drafts across method routes and remounts without running', () => {
    const descriptivesView = renderCenter({ analysisProcedure: 'descriptives' })
    fireEvent.click(screen.getByRole('checkbox', { name: 'age' }))
    descriptivesView.unmount()

    const correlationView = renderCenter({ analysisProcedure: 'correlation' })
    expect(screen.getByRole('checkbox', { name: 'age' })).not.toBeChecked()
    fireEvent.click(screen.getByRole('checkbox', { name: '自变量' }))
    correlationView.unmount()

    const restoredDescriptivesView = renderCenter({ analysisProcedure: 'descriptives' })
    expect(screen.getByRole('checkbox', { name: 'age' })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: '自变量' })).not.toBeChecked()
    restoredDescriptivesView.unmount()

    renderCenter({ analysisProcedure: 'correlation' })
    expect(screen.getByRole('checkbox', { name: '自变量' })).toBeChecked()
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()
  })

  it.each([undefined, 'BH', 'holm', 'none'])('submits the displayed group correction %s', async (method) => {
    const view = renderCenter({ analysisProcedure: 'groups' })
    expect(screen.getByLabelText('多重比较校正')).toHaveValue('holm')
    if (method) fireEvent.change(screen.getByLabelText('多重比较校正'), { target: { value: method } })
    view.unmount()
    renderCenter({ analysisProcedure: 'groups' })
    expect(screen.getByLabelText('多重比较校正')).toHaveValue(method ?? 'holm')
    fireEvent.click(screen.getByRole('checkbox', { name: '自变量' }))
    fireEvent.change(screen.getByLabelText('分组变量'), { target: { value: 'var_5_eeeeeeee' } })
    fireEvent.click(screen.getByRole('button', { name: '运行组间差异检验' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2].groupOmnibusPAdjust).toBe(method ?? 'holm')
  })

  it('resolves the selected sample context instead of submitting the all-case hash', async () => {
    vi.mocked(listAnalysisSamples).mockResolvedValue([{ id: 'sample_filtered', label: '筛选样本', includedCount: 20 }] as Awaited<ReturnType<typeof listAnalysisSamples>>)
    vi.mocked(getResolvedAnalysisContext).mockResolvedValue({ contextHash: 'selected_sample_hash', sample: { id: 'sample_filtered' } } as ResolvedAnalysisContext)
    renderCenter({ analysisContext: { contextHash: 'all_case_hash', sample: { id: 'sample_all' } } as ResolvedAnalysisContext })
    await waitFor(() => expect(screen.getByRole('option', { name: '筛选样本 · 纳入 20', hidden: true })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('checkbox', { name: 'age' }))
    fireEvent.change(screen.getByLabelText('分析样本版本（可选）'), { target: { value: 'sample_filtered' } })
    await waitFor(() => expect(getResolvedAnalysisContext).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByRole('button', { name: '运行描述统计' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: '运行描述统计' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2]).toMatchObject({ contextHash: 'selected_sample_hash', sampleVersionId: 'sample_filtered' })
  })

  it('does not execute when the selected sample context cannot be resolved', async () => {
    vi.mocked(listAnalysisSamples).mockResolvedValue([{ id: 'sample_missing', label: '旧样本', includedCount: 20 }] as Awaited<ReturnType<typeof listAnalysisSamples>>)
    vi.mocked(getResolvedAnalysisContext).mockRejectedValue(new Error('样本版本不可用，请重新选择'))
    renderCenter({ analysisContext: { contextHash: 'all_case_hash', sample: { id: 'sample_all' } } as ResolvedAnalysisContext })
    await waitFor(() => expect(screen.getByRole('option', { name: '旧样本 · 纳入 20', hidden: true })).toBeInTheDocument())
    fireEvent.click(screen.getByRole('checkbox', { name: 'age' }))
    fireEvent.change(screen.getByLabelText('分析样本版本（可选）'), { target: { value: 'sample_missing' } })
    await waitFor(() => expect(screen.getByText('样本版本不可用，请重新选择')).toBeInTheDocument())
    fireEvent.click(screen.getByRole('button', { name: '运行描述统计' }))
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()
  })

  it('starts a separate draft when upstream context identity changes', () => {
    const view = renderCenter({ analysisContext: { contextHash: 'previous_context' } as ResolvedAnalysisContext })
    fireEvent.click(screen.getByRole('checkbox', { name: 'age' }))
    view.unmount()
    renderCenter({ analysisContext: { contextHash: 'new_context' } as ResolvedAnalysisContext })
    expect(screen.getByRole('checkbox', { name: 'age' })).not.toBeChecked()
    expect(screen.getByText(/上游变化不会自动重算或覆盖旧结果/)).toBeInTheDocument()
    expect(runEmpiricalAnalysis).not.toHaveBeenCalled()
  })

  it('requires explicit regression roles and excludes overlapping variables', async () => {
    renderCenter({ analysisProcedure: 'regression' })
    expect(screen.getByLabelText('因变量（Y）')).toHaveValue('')
    expect(screen.getByRole('button', { name: '运行分层线性回归' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('因变量（Y）'), { target: { value: 'scale_y' } })
    fireEvent.click(within(screen.getByRole('group', { name: /区块 2/ })).getByRole('checkbox', { name: '自变量' }))
    expect(within(screen.getByRole('group', { name: /区块 1/ })).queryByRole('checkbox', { name: '自变量' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '运行分层线性回归' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2]).toMatchObject({ procedure: 'regression', outcomeVariableId: 'scale_y', predictorVariableIds: ['scale_x'], controlVariableIds: [], responseSurfacePredictorIds: [] })
  })

  it.each(['longitudinal', 'diary'] as const)('keeps %s inference controls within the data structure', (paradigm) => {
    renderCenter({ researchParadigm: paradigm })
    expect(screen.queryByLabelText('因变量（Y）')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '组间差异检验' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '多项式回归与响应面' })).not.toBeInTheDocument()
  })

  it('keeps nested aggregation separate from group comparison', async () => {
    renderCenter({
      analysisProcedure: 'aggregation',
      analysisContext: { dataset: { id: dataset.id }, studyContext: { value: { dependenceStructure: 'nested' } }, structure: { roles: { clusterId: 'var_7_gggggggg' } } } as unknown as ResolvedAnalysisContext,
    })
    expect(screen.getByLabelText('cluster 聚合变量')).toHaveValue('var_7_gggggggg')
    expect(screen.queryByRole('button', { name: '组间差异检验' })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('checkbox', { name: '自变量（2 题）' }))
    fireEvent.click(screen.getByRole('button', { name: '运行ICC 与聚合诊断' }))
    await waitFor(() => expect(runEmpiricalAnalysis).toHaveBeenCalledOnce())
    expect(vi.mocked(runEmpiricalAnalysis).mock.calls[0]?.[2]).toMatchObject({ procedure: 'aggregation', aggregationVariableId: 'var_7_gggggggg', groupVariableId: null, outcomeVariableId: null })
  })
})
