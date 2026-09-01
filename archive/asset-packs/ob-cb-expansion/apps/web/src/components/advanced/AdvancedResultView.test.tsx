import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { AdvancedResultView } from './AdvancedResultView'
import type { AdvancedAnalysisCapability } from '../../types'
import type { ExtendedAdvancedResultResponse } from '../../types/advanced'

describe('AdvancedResultView', () => {
  const capability: AdvancedAnalysisCapability = {
    family: 'experimental_design',
    label: '功效分析',
    status: 'experimental',
    executionAvailable: true,
    specVersion: '0.1.0',
    resultVersion: '0.1.0',
    plannedEngine: 'R',
    minimumValidation: [],
    slices: [{ id: 'experimental_design.factorial_anova.long.single_outcome', label: '组间 ANOVA', status: 'experimental', executionAvailable: true, supportBoundary: 'test' }]
  }

  const mockResult: ExtendedAdvancedResultResponse = {
    schemaVersion: '0.1.0',
    apaReports: ['For main effect, p = .42; the interval includes zero.', 'For interaction, p = .003; estimate and interval are reported.'],
    plots: [],
    run: {
      id: 'run-123',
      status: 'succeeded',
      analysisId: 'analysis-123',
      family: 'experimental_design',
      specHash: '0'.repeat(64),
      durationMilliseconds: 125,
    },
    warnings: [
      { code: 'SMALL_SAMPLE', severity: 'warning', message: '样本量较小' }
    ],
    diagnostics: [],
    sampleFlow: {
      original: 100,
      included: 98,
      excluded: 2,
      missingMethod: 'complete cases',
    },
    estimates: [
      {
        id: 'main-effect',
        label: 'Main Effect',
        estimate: 2.5,
        standardError: 0.5,
        statistic: 5.0,
        degreesOfFreedom: 96,
        pValue: 0.001,
        confidenceLower: 1.5,
        confidenceUpper: 3.5
      }
    ],
    provenance: {
      engine: 'R afex',
      engineVersion: '1.0.0',
      softwareVersions: { afex: '1.4.1' },
      dataSha256: '1'.repeat(64),
      seed: 20260714,
      specVersion: '0.1.0',
    },
    familyResult: {
      family: 'experimental_design',
      omnibusTests: [{ term: 'condition', f: 5, pValue: 0.01 }],
      estimatedMarginalMeans: [
        { condition: 'A', emmean: 2.5, SE: 0.5, df: 96, 'lower.CL': 1.5, 'upper.CL': 3.5 },
      ],
      contrasts: [{ contrast: 'A - B', estimate: 1.2, SE: 0.4, df: 96, pValue: 0.004 }],
      sphericity: null,
    },
  }

  it('renders correctly with sample flow, estimates, and warnings', () => {
    render(
      <AdvancedResultView
        result={mockResult}
        capability={capability}
        jobId="job-123"
        onNewAnalysis={vi.fn()}
      />
    )

    // Checks header
    expect(screen.getByText('功效分析 — 结果')).toBeInTheDocument()
    expect(screen.getByText('job-123')).toBeInTheDocument()

    // Checks warnings
    expect(screen.getByText('⚠ 警告 (1)')).toBeInTheDocument()
    expect(screen.getByText('样本量较小')).toBeInTheDocument()

    // Checks sample flow
    expect(screen.getByText('original')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()

    // Checks estimates
    expect(screen.getByRole('table', { name: '参数估计' })).toBeInTheDocument()
    expect(screen.getByText('Main Effect')).toBeInTheDocument()
    expect(screen.getByText('2.5000')).toBeInTheDocument()

    // Checks p-value formatting (0.001 formatting -> 0.0010)
    expect(screen.getByText('0.0010')).toBeInTheDocument()
    expect(screen.getByText('[1.5000, 3.5000]')).toBeInTheDocument()
    expect(screen.getByText('For main effect, p = .42; the interval includes zero.')).toBeInTheDocument()
    expect(screen.getByText('For interaction, p = .003; estimate and interval are reported.')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /^Estimated marginal means and confidence intervals/ })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Estimated marginal means' })).toBeInTheDocument()
    expect(screen.getByRole('table', { name: 'Contrasts' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '导出论文复现包' })).toHaveAttribute(
      'href',
      '/api/v1/advanced-analyses/job-123/export',
    )
    expect(screen.getByRole('link', { name: '导出复现包（含数据）' })).toHaveAttribute(
      'href',
      '/api/v1/advanced-analyses/job-123/export?include_data=true',
    )
  })

  it('renders the parsed power result and preserves its effect-size metric', () => {
    const powerResult = {
      ...mockResult,
      run: { ...mockResult.run, family: 'power_analysis' as const },
      estimates: [{ id: 'power', label: 'Achieved power', estimate: 0.8 }],
      familyResult: {
        family: 'power_analysis' as const,
        solveFor: 'effect_size' as const,
        solvedValue: 0.101980903171092,
        achievedPower: 0.8,
        parameters: {
          effectSizeMetric: 'r_squared_change',
          solvedValueMetric: 'r_squared_change',
        },
      },
    } as ExtendedAdvancedResultResponse
    const powerCapability: AdvancedAnalysisCapability = {
      ...capability,
      family: 'power_analysis',
      label: '回归与组间 ANOVA 解析功效',
      slices: [{ id: 'power_analysis.analytic.regression', label: '回归解析功效', status: 'experimental', executionAvailable: true, supportBoundary: 'test' }],
    }

    render(
      <AdvancedResultView
        result={powerResult}
        capability={powerCapability}
        jobId="power-job"
        onNewAnalysis={vi.fn()}
      />
    )

    expect(screen.getByRole('heading', { name: '解析功效摘要' })).toBeInTheDocument()
    expect(screen.getByText('最小可检测效应')).toBeInTheDocument()
    expect(screen.getByText('0.1020 (R² change)')).toBeInTheDocument()
    expect(screen.getByText('80.0%')).toBeInTheDocument()
  })
})
