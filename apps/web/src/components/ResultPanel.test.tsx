import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ResultBundle } from '../types'
import { ResultPanel } from './ResultPanel'

const result: ResultBundle = {
  schemaVersion: '0.1.0',
  jobStatus: 'completed',
  estimationStatus: 'succeeded',
  inferenceStatus: 'reliable',
  publicationEligibility: 'conditional',
  run: { id: 'run_example_1234567890', status: 'succeeded', modelId: 'm4', modelHash: 'a'.repeat(64) },
  sampleFlow: { original: 30, included: 30, excluded: 0, missingMethod: 'complete_cases_per_model' },
  equations: [],
  effects: [
    { id: 'a', type: 'path', label: 'a', estimate: 0.61 },
    { id: 'b', type: 'path', label: 'b', estimate: 0.72 },
    { id: 'direct', type: 'direct', label: 'c_prime', estimate: 0.21 },
    {
      id: 'indirect',
      type: 'indirect',
      label: 'a_x_b',
      estimate: 0.4392,
      confidenceInterval: { level: 0.95, lower: 0.2, upper: 0.66, method: 'bootstrap_percentile' },
    },
  ],
  warnings: [],
  provenance: {
    engine: 'researchpath-r',
    engineVersion: '0.1.0',
    rVersion: 'R 4.6.1',
    jsonliteVersion: '2.0.0',
    dataSha256: 'b'.repeat(64),
  },
}

describe('ResultPanel', () => {
  it('renders the indirect effect and runs from a semantic button', () => {
    const onRun = vi.fn()
    render(<ResultPanel result={result} isRunning={false} onRun={onRun} />)

    expect(screen.getAllByText('0.439')).toHaveLength(2)
    expect(screen.getAllByText('[0.200, 0.660]')).toHaveLength(2)
    expect(screen.queryByText(/密集纵向动态剖析器/)).not.toBeInTheDocument()
    expect(screen.queryByText(/纵向追踪泳道画布/)).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重新运行当前冻结版本' }))
    expect(onRun).toHaveBeenCalledOnce()
  })

  it('renders APA table exporter buttons when academicInterpretation and apaTables exist', () => {
    const resultWithInterpretation: ResultBundle = {
      ...result,
      academicInterpretation: '中介效应显著。',
      apaTables: '| 效应 | B | SE |\n|---|---|---|\n| a*b | 0.439 | 0.068 |',
    }
    render(<ResultPanel result={resultWithInterpretation} isRunning={false} onRun={() => {}} />)

    expect(screen.getByText('中文自动解读与 APA 报告规范')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Word 三线表/i })[0]).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /LaTeX/i })[0]).toBeInTheDocument()
  })

  it('labels McFadden R² from the engine-typed rSquaredType field', () => {
    const logisticResult: ResultBundle = {
      ...result,
      equations: [
        {
          id: 'equation_y',
          outcomeRole: 'y' as const,
          formula: 'y ~ x',
          rSquared: 0.24,
          adjustedRSquared: 0.22,
          nagelkerkeRSquared: 0.31,
          rSquaredType: 'mcfadden_pseudo_r_squared',
          modelFamily: 'binomial_logit',
          coefficients: [
            {
              equationId: 'equation_y',
              term: 'x',
              estimate: 0.5,
              standardError: 0.2,
              statistic: 2.5,
              pValue: 0.01,
              confidenceInterval: { level: 0.95, lower: 0.11, upper: 0.89, method: 'wald_z' },
            },
          ],
        },
      ],
    }
    render(<ResultPanel result={logisticResult} isRunning={false} onRun={() => {}} />)

    expect(screen.getByText(/Y 方程 · McFadden R² 0\.240，Nagelkerke R² 0\.310/)).toBeInTheDocument()
    expect(screen.queryByText(/调整后 R²/)).not.toBeInTheDocument()
  })
})
