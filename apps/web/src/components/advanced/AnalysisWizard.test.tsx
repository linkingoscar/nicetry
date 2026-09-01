import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AnalysisWizard } from './AnalysisWizard'
import * as advancedApi from '../../api/advanced'
import type { AdvancedAnalysisCapability } from '../../types'
import type {
  AdvancedAnalysisValidation,
  AdvancedJobResponse,
  PowerAnalysisSpec,
} from '../../types/advanced'

vi.mock('../../api/advanced')

describe('AnalysisWizard', () => {
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

  const powerSpec: PowerAnalysisSpec = {
    schemaVersion: '0.1.0',
    analysisId: 'test-id',
    name: '测试功效分析',
    family: 'power_analysis',
    confidenceLevel: 0.95,
    seed: 20260714,
    designFamily: 'regression',
    method: 'analytic',
    solveFor: 'sample_size',
    alpha: 0.05,
    targetPower: 0.8,
    effectSize: { metric: 'cohens_f2', value: 0.15 },
    predictors: 3,
    groups: 1,
    simulations: 5000,
    alternative: 'two_sided',
    roundingRule: 'ceil',
  }

  const validation: AdvancedAnalysisValidation = {
    valid: true,
    family: 'power_analysis',
    capabilityId: 'power_analysis.analytic.regression',
    sliceId: 'power_analysis.analytic.regression',
    sliceStatus: 'experimental',
    implementationStatus: 'experimental',
    executionAvailable: true,
    spec: powerSpec,
    warnings: [],
  }

  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('renders initial config step', () => {
    render(<AnalysisWizard capability={capability} onJobStarted={vi.fn()} />)
    expect(screen.getByText('功效分析 — 规格配置')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '验证规格' })).toBeInTheDocument()
  })

  it('validates spec and moves to validation summary', async () => {
    vi.mocked(advancedApi.validateAdvancedAnalysisSpec).mockResolvedValue(validation)

    render(<AnalysisWizard capability={capability} onJobStarted={vi.fn()} />)

    const validateBtn = screen.getByRole('button', { name: '验证规格' })
    fireEvent.click(validateBtn)

    await waitFor(() => {
      expect(screen.getByText('验证摘要')).toBeInTheDocument()
    })

    expect(screen.getByText(/规格有效，可以提交运行/)).toBeInTheDocument()
  })

  it('passes the active dataset to validation and execution', async () => {
    vi.mocked(advancedApi.validateAdvancedAnalysisSpec).mockResolvedValue(validation)
    const mockJob: AdvancedJobResponse = {
      id: 'job-dataset',
      status: 'queued',
      stage: 'queued',
      progress: 0,
      analysisId: 'test-id',
      family: 'power_analysis',
      specHash: 'test-spec-hash',
      cancelRequested: false,
      createdAt: '2026-07-17T00:00:00.000Z',
      updatedAt: '2026-07-17T00:00:00.000Z',
    }
    vi.mocked(advancedApi.runAdvancedAnalysis).mockResolvedValue(mockJob)

    render(
      <AnalysisWizard
        capability={capability}
        datasetId="dataset-active"
        onJobStarted={vi.fn()}
      />,
    )

    fireEvent.click(screen.getByRole('button', { name: '验证规格' }))
    const submitBtn = await screen.findByRole('button', { name: '提交后台运行' })
    expect(advancedApi.validateAdvancedAnalysisSpec).toHaveBeenCalledWith(
      expect.objectContaining({ family: 'power_analysis' }),
      'dataset-active',
    )

    fireEvent.click(submitBtn)
    await waitFor(() => {
      expect(advancedApi.runAdvancedAnalysis).toHaveBeenCalledWith(powerSpec, 'dataset-active')
    })
  })

  it('submits job and calls onJobStarted', async () => {
    vi.mocked(advancedApi.validateAdvancedAnalysisSpec).mockResolvedValue(validation)

    const mockJob: AdvancedJobResponse = {
      id: 'job-123',
      status: 'queued',
      stage: 'queued',
      progress: 0,
      analysisId: 'test-id',
      family: 'power_analysis',
      specHash: 'test-spec-hash',
      cancelRequested: false,
      createdAt: '2026-07-17T00:00:00.000Z',
      updatedAt: '2026-07-17T00:00:00.000Z',
    }
    vi.mocked(advancedApi.runAdvancedAnalysis).mockResolvedValue(mockJob)

    const onJobStarted = vi.fn()

    render(<AnalysisWizard capability={capability} onJobStarted={onJobStarted} />)

    // Go to step 2
    fireEvent.click(screen.getByRole('button', { name: '验证规格' }))

    // Wait for step 2
    const submitBtn = await screen.findByRole('button', { name: '提交后台运行' })

    // Click submit
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(onJobStarted).toHaveBeenCalledWith(mockJob)
    })
  })
})
