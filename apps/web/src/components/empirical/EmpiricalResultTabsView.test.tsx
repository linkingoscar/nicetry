import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EmpiricalResultTabsView } from './EmpiricalResultTabsView'
import type { EmpiricalAnalysisReport, EmpiricalAnalysisSegmentMap } from '../../types'

const readyQuery = <Data,>(data: Data) => ({
  data,
  isLoading: false,
  isError: false,
  error: null,
})

describe('EmpiricalResultTabsView measurement fallbacks', () => {
  it('does not present a computable small-sample CFA as confirmatory evidence', () => {
    render(
      <EmpiricalResultTabsView
        activeTab="overview"
        reportId="empirical_small_n"
        datasetId="dataset_test"
        measurementVersion={1}
        reportOptions={{}}
        queries={{
          summary: readyQuery({
          sample: {
            rowCount: 24,
            itemCompleteCases: 24,
            constructCount: 3,
            measurementAdequacy: {
              status: 'caution',
              completeCases: 24,
              itemCount: 12,
              estimatedParameterCount: 27,
              casesPerParameter: 0.89,
              minimumCompleteCasesGuardrail: 100,
              minimumCasesPerParameterGuardrail: 5,
              parameterCountSource: 'fitted model free-parameter count',
              interpretation: 'exploratory only',
              ruleNature: 'transparent platform guardrail',
            },
          },
          missingDataReport: null,
          descriptives: [],
          frequencies: [],
          factorability: {
            kmo: 0.82,
            bartlett: { statistic: 40, degreesOfFreedom: 12, pValue: 0.001 },
            completeCases: 24,
          },
          commonMethodBias: {
            available: true,
            completeCases: 24,
            itemCount: 12,
            firstFactorVariancePercent: 31,
            eigenvaluesAboveOne: 3,
            method: 'diagnostic',
          },
          resultAvailability: {
            groups: 'not_requested',
            regression: 'not_requested',
            advanced: 'not_requested',
            longitudinal: 'not_requested',
            diary: 'not_requested',
          },
          efa: { factorCount: 3 },
          cfa: {
            available: true,
            validForConfirmatoryInterpretation: false,
          },
        }),
        correlation: readyQuery(null),
        efaCfa: readyQuery(null),
        validity: readyQuery(null),
        regression: readyQuery(null),
        }}
        showToast={vi.fn()}
      />,
    )

    expect(screen.getByText('可计算 · 解释受限')).toBeInTheDocument()
    expect(screen.getByText('样本信息不足以支持稳定的确认性测量结论')).toBeInTheDocument()
    expect(screen.getByText(/这不是通用样本量定理/)).toBeInTheDocument()
    expect(screen.queryByText('数据正态性与因子适合度良好')).not.toBeInTheDocument()
  })

  it('labels EFA and validity fallback outputs next to the affected results', () => {
    const efaExecution = {
      requestedMethod: 'maximum_likelihood_factanal_varimax',
      executedMethod: 'principal_components_varimax',
      fallbackApplied: true,
      fallbackCode: 'EFA_FACTANAL_FALLBACK_PCA',
      fallbackReason: 'forced estimation failure',
      affectedOutputs: ['factorLoadings'],
      interpretationBoundary: '当前结果为主成分分析，不是共同因子模型。',
    }
    const validityExecution = {
      requestedMethod: 'CFA standardized loadings',
      executedMethod: 'single-factor eigen approximation',
      fallbackApplied: true,
      fallbackCode: 'CFA_UNAVAILABLE_FALLBACK_SINGLE_FACTOR_EIGEN',
      fallbackReason: 'CFA did not converge',
      affectedOutputs: ['compositeReliability'],
      interpretationBoundary: '当前结果不是 CFA 标准化解。',
    }

    render(
      <EmpiricalResultTabsView
        activeTab="measurement"
        reportId="empirical_test"
        datasetId="dataset_test"
        measurementVersion={1}
        reportOptions={{}}
        queries={{
          summary: readyQuery({
          sample: { rowCount: 100, itemCompleteCases: 95, constructCount: 1 },
          missingDataReport: null,
          descriptives: [],
          frequencies: [],
          factorability: {
            kmo: 0.8,
            bartlett: { statistic: 10, degreesOfFreedom: 3, pValue: 0.01 },
            completeCases: 95,
          },
          commonMethodBias: {
            available: true,
            completeCases: 95,
            itemCount: 3,
            firstFactorVariancePercent: 30,
            eigenvaluesAboveOne: 1,
            method: 'unrotated_single_factor',
          },
          resultAvailability: {
            groups: 'not_requested',
            regression: 'not_requested',
            advanced: 'not_requested',
            longitudinal: 'not_requested',
            diary: 'not_requested',
          },
          efa: { factorCount: 1 },
          cfa: { available: false, reason: 'CFA did not converge' },
        }),
        correlation: readyQuery(null),
        efaCfa: readyQuery({
          efa: {
            available: false,
            factorCount: 1,
            factorLabels: ['F1'],
            method: 'principal_components_varimax',
            methodExecution: efaExecution,
            rotation: 'varimax',
            eigenvalues: [],
            loadings: [],
          },
          cfa: { available: false, reason: 'CFA did not converge' },
        }),
        validity: readyQuery({
          validity: {
            methodExecution: validityExecution,
            constructs: [{
              constructId: 'construct_a',
              label: '构念 A',
              scoreId: 'score_a',
              alpha: 0.8,
              omega: 0.82,
              compositeReliability: 0.81,
              averageVarianceExtracted: 0.55,
              sqrtAve: 0.74,
              loadingSource: 'single-factor eigen fallback',
              discriminantValidityPass: null,
            }],
            constructLabels: ['构念 A'],
            fornellLarcker: [[0.74]],
            htmt: [[1]],
          },
        }),
        regression: readyQuery(null),
        }}
        showToast={vi.fn()}
      />,
    )

    expect(screen.getByText('EFA 已使用降级方法')).toBeInTheDocument()
    expect(screen.getByText('效度指标使用近似载荷')).toBeInTheDocument()
    expect(screen.getByText('单因子特征分解近似')).toBeInTheDocument()
    expect(screen.getByText(/forced estimation failure/)).toBeInTheDocument()
    expect(screen.getAllByText(/CFA did not converge/)).toHaveLength(2)
  })
})

describe('EmpiricalResultTabsView EFA statistical-world disclosure', () => {
  const baseSummary: EmpiricalAnalysisSegmentMap['summary'] = {
    sample: { rowCount: 200, itemCompleteCases: 200, constructCount: 1 },
    missingDataReport: null,
    descriptives: [],
    frequencies: [],
    factorability: { kmo: 0.8, bartlett: { statistic: 10, degreesOfFreedom: 3, pValue: 0.01 }, completeCases: 200 },
    commonMethodBias: {
      available: true, completeCases: 200, itemCount: 8,
      firstFactorVariancePercent: 30, eigenvaluesAboveOne: 1, method: 'diagnostic',
    },
    resultAvailability: {
      groups: 'not_requested', regression: 'not_requested', advanced: 'not_requested',
      longitudinal: 'not_requested', diary: 'not_requested',
    },
    efa: { factorCount: 1 },
    cfa: { available: false, reason: 'not requested' },
  }

  const renderMeasurement = (efaCfa: Pick<EmpiricalAnalysisReport, 'efa' | 'cfa'>) =>
    render(
      <EmpiricalResultTabsView
        activeTab="measurement"
        reportId="empirical_pa"
        datasetId="dataset_test"
        measurementVersion={1}
        reportOptions={{}}
        queries={{
          summary: readyQuery(baseSummary),
          correlation: readyQuery(null),
          efaCfa: readyQuery(efaCfa),
          validity: readyQuery({ validity: { constructs: [], constructLabels: [], fornellLarcker: [], htmt: [] } }),
          regression: readyQuery(null),
        }}
        showToast={vi.fn()}
      />,
    )

  it('displays parallel analysis correlation/simulation metadata when available', () => {
    renderMeasurement({
      efa: {
        available: true,
        factorCount: 1,
        factorLabels: ['F1'],
        method: 'ml',
        rotation: 'promax',
        correlationType: 'polychoric',
        eigenvalues: [4.2, 1.1, 0.9],
        loadings: [],
        parallelAnalysis: {
          available: true,
          recommendedFactorCount: 1,
          iterations: 100,
          seed: 42,
          quantile: 0.95,
          correlationType: 'polychoric',
          simulationType: 'ordinal_threshold_preserving',
          simulatedEigenvalues: [1.3, 1.2, 1.1],
        },
      },
      cfa: { available: false, reason: 'not requested' },
    })

    // The recommendation count sits inside a <strong> and the metadata inside
    // interpolated text nodes; regex matchers run over the paragraph text.
    expect(screen.getByText(/100 次模拟/)).toBeInTheDocument()
    expect(screen.getByText(/polychoric（序数题项）/)).toBeInTheDocument()
    expect(screen.getByText(/序数阈值保留模拟/)).toBeInTheDocument()
  })

  it('reports ordinal parallel analysis as unavailable instead of silently using Pearson', () => {
    renderMeasurement({
      efa: {
        available: true,
        factorCount: 1,
        factorLabels: ['F1'],
        method: 'ml',
        rotation: 'promax',
        correlationType: 'polychoric',
        eigenvalues: [4.2, 1.1, 0.9],
        loadings: [],
        parallelAnalysis: {
          available: false,
          reason: 'unsupported_for_ordinal_correlation',
          correlationType: 'polychoric',
          simulationType: 'ordinal_threshold_preserving',
        },
      },
      cfa: { available: false, reason: 'not requested' },
    })

    expect(screen.getByText('平行分析不可用')).toBeInTheDocument()
    expect(screen.getByText(/lavaan 不可用或题项类别结构异常/)).toBeInTheDocument()
    expect(screen.getByText(/不会以 Pearson 相关静默替代 polychoric/)).toBeInTheDocument()
  })

  it('discloses numerical fallbacks from the EFA diagnostics', () => {
    renderMeasurement({
      efa: {
        available: true,
        factorCount: 1,
        factorLabels: ['F1'],
        method: 'paf',
        rotation: 'none',
        eigenvalues: [4.2, 1.1, 0.9],
        loadings: [],
        diagnostics: {
          items: [],
          numericalFallbacks: [
            {
              stage: 'initial_communality',
              requested: 'smc',
              used: 'fixed_0_5',
              reason: 'correlation matrix inversion failed',
            },
          ],
        },
      },
      cfa: { available: false, reason: 'not requested' },
    })

    expect(screen.getByText('EFA 使用了数值回退')).toBeInTheDocument()
    expect(screen.getByText(/阶段 initial_communality/)).toBeInTheDocument()
    expect(screen.getByText(/请求 smc，实际使用 fixed_0_5/)).toBeInTheDocument()
    expect(screen.getByText(/correlation matrix inversion failed/)).toBeInTheDocument()
  })
})
