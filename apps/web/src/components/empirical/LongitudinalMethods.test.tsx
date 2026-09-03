import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type {
  DiaryMultilevelOptions,
  DiaryMultilevelResult,
  LongitudinalPanelOptions,
} from '../../types'
import { DiaryDsemResult } from './DiaryDsemResult'
import { DiaryGlmmEvidenceResult } from './DiaryGlmmEvidenceResult'
import { DiaryMultilevelConfig } from './DiaryMultilevelConfig'
import { LongitudinalPanelConfig } from './LongitudinalPanelConfig'

const variables = [
  { id: 'day', label: 'day' },
  { id: 'x1', label: 'X T1' },
  { id: 'y1', label: 'Y T1' },
  { id: 'x2', label: 'X T2' },
  { id: 'y2', label: 'Y T2' },
  { id: 'x3', label: 'X T3' },
  { id: 'y3', label: 'Y T3' },
]
const subjects = [{ id: 'person_id', label: 'person_id' }]

function LongitudinalHarness() {
  const [value, setValue] = useState<LongitudinalPanelOptions | null>(null)
  return (
    <LongitudinalPanelConfig
      value={value}
      variables={variables}
      itemGroups={[]}
      subjectCandidates={subjects}
      onChange={setValue}
    />
  )
}

function DiaryHarness() {
  const [value, setValue] = useState<DiaryMultilevelOptions | null>(null)
  return (
    <DiaryMultilevelConfig
      value={value}
      variables={variables}
      itemGroups={[]}
      subjectCandidates={subjects}
      onChange={setValue}
    />
  )
}

describe('longitudinal empirical method configuration', () => {
  it('creates a three-wave RI-CLPM configuration by default', () => {
    render(<LongitudinalHarness />)
    fireEvent.click(screen.getByRole('checkbox', { name: /启用纵向面板分析/ }))
    expect(screen.getByLabelText('波次 1 标签')).toHaveValue('T1')
    expect(screen.getByLabelText('波次 3 标签')).toHaveValue('T3')
    expect(screen.getByLabelText('被试 ID')).toHaveValue('person_id')
    fireEvent.click(screen.getByRole('checkbox', {
      name: /估计双向交叉滞后路径的功效/,
    }))
    expect(screen.getByLabelText(/候选样本量/)).toHaveValue('200, 300, 500, 800')
  })

  it('switches diary analysis from LMM to multilevel mediation', () => {
    render(<DiaryHarness />)
    fireEvent.click(screen.getByRole('checkbox', { name: /启用日记研究二层模型/ }))
    fireEvent.change(screen.getByLabelText('分析类型'), { target: { value: 'mediation' } })
    expect(screen.getByLabelText('中介变量 M')).toBeInTheDocument()
    expect(screen.getByLabelText('中介结构')).toHaveValue('1-1-1')
  })

  it('configures an ESM person-by-occasion Monte Carlo grid', () => {
    render(<DiaryHarness />)
    fireEvent.click(screen.getByRole('checkbox', { name: /启用日记研究二层模型/ }))
    fireEvent.click(screen.getByRole('checkbox', {
      name: /模拟当前随机效应与时间结构/,
    }))
    expect(screen.getByLabelText('候选人数')).toHaveValue('50, 80, 120')
    expect(screen.getByLabelText('每人候选测量次数')).toHaveValue('7, 10, 14')
  })

  it('exposes GLMM outcome families and crossed clustering only when selected', () => {
    render(<DiaryHarness />)
    fireEvent.click(screen.getByRole('checkbox', { name: /启用日记研究二层模型/ }))
    fireEvent.change(screen.getByLabelText('分析类型'), { target: { value: 'glmm' } })
    expect(screen.getByLabelText('结局分布')).toHaveValue('binomial')
    fireEvent.change(screen.getByLabelText('聚类结构'), {
      target: { value: 'cross_classified' },
    })
    expect(screen.getByLabelText('交叉分类单元')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('结局分布'), {
      target: { value: 'poisson' },
    })
    fireEvent.change(screen.getByLabelText('计数过程'), {
      target: { value: 'zero_inflated' },
    })
    expect(screen.getByLabelText('零过程规格')).toHaveValue('intercept_only')
    expect(screen.getByLabelText('模拟诊断次数')).toHaveValue(250)
  })

  it('configures Bayesian DSEM sampling without exposing incompatible controls', () => {
    render(<DiaryHarness />)
    fireEvent.click(screen.getByRole('checkbox', { name: /启用日记研究二层模型/ }))
    fireEvent.change(screen.getByLabelText('分析类型'), {
      target: { value: 'bayesian_dsem' },
    })
    expect(screen.getByLabelText('链数')).toHaveValue(4)
    expect(screen.getByLabelText('每链迭代')).toHaveValue(2000)
    expect(screen.getByLabelText('每链绘图抽样')).toHaveValue(300)
    expect(screen.getByLabelText('预测检验重复数')).toHaveValue(200)
    expect(screen.queryByLabelText('Level 2 调节变量')).not.toBeInTheDocument()
  })

  it('renders bounded DSEM traces and modern diagnostics', () => {
    const result = {
      analysisType: 'bayesian_dsem',
      methodNotice: '观测变量动态关联。',
      mcmcDiagnostics: {
        chains: 2,
        iterationsPerChain: 500,
        warmupPerChain: 250,
        thin: 1,
        retainedPerChain: 250,
        maximumRHat: 1.001,
        minimumEffectiveSampleSize: 180,
        minimumBulkEffectiveSampleSize: 190,
        minimumTailEffectiveSampleSize: 180,
        effectiveSampleSizeThreshold: 100,
        diagnosticMethod: 'rank-normalized',
        stationarity: {
          yAutoregressiveWithinUnitInterval: true,
          xAutoregressiveWithinUnitInterval: true,
        },
      },
      posteriorEffects: [],
      posteriorDraws: [{
        id: 'y_cross_lag',
        label: 'X→Y',
        chains: [
          { chain: 1, iterations: [251, 252], values: [0.1, 0.2] },
          { chain: 2, iterations: [251, 252], values: [0.12, 0.18] },
        ],
      }],
      posteriorPredictive: {
        yBayesianRSquared: 0.2,
        xBayesianRSquared: 0.1,
        checks: [],
      },
    } as unknown as DiaryMultilevelResult
    render(<DiaryDsemResult result={result} metric={(value) => String(value ?? '—')} />)
    expect(screen.getByText('最小 bulk ESS')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /MCMC 迹线图/ })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /后验分布图/ })).toBeInTheDocument()
  })

  it('reports zero-process effects separately from count effects', () => {
    const result = {
      analysisType: 'glmm',
      countModel: 'hurdle',
      methodNotice: '门槛过程与正计数过程分别解释。',
      distributionDiagnostics: {
        pearsonDispersion: 1,
        observedZeroRate: 0.4,
        expectedZeroRate: 0.38,
        zeroRateDifference: 0.02,
        simulationCount: 250,
        dispersionRatio: 1.05,
        dispersionPValue: 0.3,
        zeroInflationPValue: 0.4,
      },
      zeroProcessEffects: [{
        term: '(Intercept)',
        label: '截距',
        estimate: -0.4,
        standardError: 0.1,
        degreesOfFreedom: null,
        statistic: -4,
        pValue: 0.001,
        lower: -0.6,
        upper: -0.2,
        exponentiatedEstimate: 0.67,
        exponentiatedLower: 0.55,
        exponentiatedUpper: 0.82,
      }],
      countModelComparison: [],
    } as unknown as DiaryMultilevelResult
    render(
      <DiaryGlmmEvidenceResult
        result={result}
        metric={(value) => String(value ?? '—')}
        probability={(value) => String(value ?? '—')}
      />,
    )
    expect(screen.getByText('零值/门槛过程')).toBeInTheDocument()
    expect(screen.getByText(/分别解释/)).toBeInTheDocument()
  })
})
