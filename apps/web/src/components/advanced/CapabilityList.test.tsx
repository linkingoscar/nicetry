import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { CapabilityList } from './CapabilityList'
import * as advancedApi from '../../api/advanced'
import type { AdvancedAnalysisCapability } from '../../types'

vi.mock('../../api/advanced')

describe('CapabilityList', () => {
  const mockCapabilities: AdvancedAnalysisCapability[] = [
    {
      family: 'experimental_design',
      label: '实验设计',
      status: 'supported',
      executionAvailable: true,
      specVersion: '0.1.0',
      resultVersion: '0.1.0',
      plannedEngine: 'R',
      minimumValidation: [],
      slices: [{ id: 'experimental_design.factorial_anova.long.single_outcome', label: '组间 ANOVA', status: 'supported', executionAvailable: true, supportBoundary: 'test' }]
    },
    {
      family: 'power_analysis',
      label: '功效分析',
      status: 'experimental',
      executionAvailable: true,
      specVersion: '0.1.0',
      resultVersion: '0.1.0',
      plannedEngine: 'R',
      minimumValidation: [],
      slices: [{ id: 'power_analysis.analytic.regression', label: '回归解析功效', status: 'experimental', executionAvailable: true, supportBoundary: 'test' }]
    },
    {
      family: 'questionnaire_measurement',
      label: '高级测量（停用）',
      status: 'experimental',
      executionAvailable: false,
      specVersion: '0.1.0',
      resultVersion: '0.1.0',
      plannedEngine: 'R',
      minimumValidation: [],
      slices: [{ id: 'questionnaire_measurement.irt', label: 'IRT', status: 'planned', executionAvailable: false, supportBoundary: 'test' }]
    }
  ]

  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders loading state initially', () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockReturnValue(new Promise(() => {}))
    render(<CapabilityList onSelect={vi.fn()} />)
    expect(screen.getByText('正在加载可用的高级分析方法...')).toBeInTheDocument()
  })

  it('renders capabilities, filtering out non-executable ones', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockResolvedValue({
      schemaVersion: '0.1.0',
      capabilities: mockCapabilities
    })

    render(<CapabilityList onSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.queryByText('正在加载可用的高级分析方法...')).not.toBeInTheDocument()
    })

    // Executable capabilities are shown
    expect(screen.getByText('实验设计')).toBeInTheDocument()
    expect(screen.getByText('功效分析')).toBeInTheDocument()

    // Non-executable capability is NOT shown
    expect(screen.queryByText('高级测量（停用）')).not.toBeInTheDocument()
  })

  it('requires both an executable family and an executable slice before exposing a method', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockResolvedValue({
      schemaVersion: '0.1.0',
      capabilities: [
        ...mockCapabilities,
        {
          family: 'multiple_imputation',
          label: '多重插补（没有可运行切片）',
          status: 'experimental',
          executionAvailable: true,
          specVersion: '0.1.0',
          resultVersion: '0.1.0',
          plannedEngine: 'R',
          minimumValidation: [],
          slices: [{ id: 'multiple_imputation.mice', label: 'MICE', status: 'experimental', executionAvailable: false, supportBoundary: 'test' }],
        },
      ],
    })

    render(<CapabilityList onSelect={vi.fn()} />)

    expect(await screen.findByText('实验设计')).toBeInTheDocument()
    expect(screen.queryByText('多重插补（没有可运行切片）')).not.toBeInTheDocument()
  })

  it('calls onSelect when a capability is clicked', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockResolvedValue({
      schemaVersion: '0.1.0',
      capabilities: mockCapabilities
    })

    const onSelect = vi.fn()
    const user = userEvent.setup()

    render(<CapabilityList onSelect={onSelect} />)

    const button = await screen.findByRole('button', { name: /功效分析/i })
    await user.click(button)

    expect(onSelect).toHaveBeenCalledWith(mockCapabilities[1])
  })

  it('keeps power available before data is prepared and gates data-backed methods', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockResolvedValue({
      schemaVersion: '0.1.0',
      capabilities: mockCapabilities
    })

    render(<CapabilityList onSelect={vi.fn()} hasDataset={false} />)

    expect(await screen.findByRole('button', { name: /实验设计.*需先准备数据/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /功效分析.*实验性/i })).toBeEnabled()
  })

  it('filters the catalog to the families allowed by the current workflow', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockResolvedValue({
      schemaVersion: '0.1.0',
      capabilities: mockCapabilities,
    })

    render(
      <CapabilityList
        onSelect={vi.fn()}
        hasDataset={false}
        allowedFamilies={['power_analysis']}
        title="样本量、功效与精度"
      />,
    )

    expect(await screen.findByText('样本量、功效与精度')).toBeInTheDocument()
    expect(screen.getByText('功效分析')).toBeInTheDocument()
    expect(screen.queryByText('实验设计')).not.toBeInTheDocument()
  })

  it('shows error state if API fails', async () => {
    vi.mocked(advancedApi.getAdvancedAnalysisCapabilities).mockRejectedValue(new Error('Network Error'))

    render(<CapabilityList onSelect={vi.fn()} />)

    await waitFor(() => {
      expect(screen.getByText('加载失败')).toBeInTheDocument()
      expect(screen.getByText('Network Error')).toBeInTheDocument()
    })
  })
})
