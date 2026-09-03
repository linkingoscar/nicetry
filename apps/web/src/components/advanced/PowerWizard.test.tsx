import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import {
  normalizePowerSpecForSlice,
  PowerWizard,
  powerDesignFamilyForSlice,
  type PowerWizardSpec,
} from './PowerWizard'

const baseSpec: PowerWizardSpec = {
  family: 'power_analysis',
  method: 'analytic',
  designFamily: 'regression',
  solveFor: 'sample_size',
  alpha: 0.05,
  targetPower: 0.8,
  effectSize: { metric: 'cohens_f2', value: 0.15 },
  alternative: 'two_sided',
}

describe('PowerWizard', () => {
  it('renders research notation instead of raw LaTeX or internal metric IDs', () => {
    const { container } = render(<PowerWizard spec={baseSpec} onChange={vi.fn()} />)

    expect(screen.getByText('显著性水平 α')).toBeInTheDocument()
    expect(screen.getByText('目标统计功效（1 − β）')).toBeInTheDocument()
    expect(screen.getByText("Cohen's f²")).toBeInTheDocument()
    expect(container).not.toHaveTextContent('$\\alpha$')
    expect(container).not.toHaveTextContent('cohens_f2')
  })

  it('maps an unscoped design change to the corresponding effect-size metric', async () => {
    const onChange = vi.fn()
    render(<PowerWizard spec={baseSpec} onChange={onChange} />)

    await userEvent.selectOptions(
      screen.getByLabelText(/设计类型/),
      't_test',
    )

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      designFamily: 't_test',
      groups: 2,
      effectSize: { metric: 'cohens_d', value: 0.15 },
    }))
  })

  it('locks analytic method cards to the method and design declared by their capability slice', () => {
    const onChange = vi.fn()
    render(
      <PowerWizard
        spec={{ ...baseSpec, method: 'monte_carlo' }}
        onChange={onChange}
        sliceId="power_analysis.analytic.t_test"
      />,
    )

    expect(powerDesignFamilyForSlice('power_analysis.analytic.t_test')).toBe('t_test')
    expect(screen.getByLabelText(/设计类型/)).toBeDisabled()
    expect(screen.getByLabelText(/设计类型/)).toHaveValue('t_test')
    expect(screen.getByText("Cohen's d")).toBeInTheDocument()
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      method: 'analytic',
      designFamily: 't_test',
      groups: 2,
      effectSize: { metric: 'cohens_d', value: 0.15 },
    }))
  })

  it('adds the required current N when solving achieved power', () => {
    expect(normalizePowerSpecForSlice({ ...baseSpec, solveFor: 'power' }, 'power_analysis.analytic.regression')).toMatchObject({
      method: 'analytic',
      solveFor: 'power',
      sampleSize: 200,
      alternative: 'two_sided',
      effectSize: { metric: 'cohens_f2', value: 0.15 },
    })
  })

  it('removes a known effect value and supplies its metric when solving MDES', () => {
    const normalized = normalizePowerSpecForSlice(
      { ...baseSpec, solveFor: 'effect_size' },
      'power_analysis.analytic.regression',
    )
    expect(normalized.sampleSize).toBe(200)
    expect(normalized.effectSize).toBeUndefined()
    expect(normalized.effectSizeMetric).toBe('cohens_f2')
  })

  it('normalizes unsupported guided Monte Carlo settings to the registered method and regression DGP boundary', () => {
    const normalized = normalizePowerSpecForSlice({
      ...baseSpec,
      method: 'analytic',
      designFamily: 't_test',
      solveFor: 'ci_width',
      alternative: 'one_sided',
      targetCIWidth: 0.05,
    }, 'power_analysis.monte_carlo')

    expect(normalized).toMatchObject({
      method: 'monte_carlo',
      designFamily: 'regression',
      solveFor: 'sample_size',
      alternative: 'two_sided',
    })
    expect(normalized.sampleSize).toBeUndefined()
    expect(normalized.targetCIWidth).toBeUndefined()
  })
})
