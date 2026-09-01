import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { PowerWizard, type PowerWizardSpec } from './PowerWizard'

const baseSpec: PowerWizardSpec = {
  family: 'power_analysis',
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

  it('maps the selected design to the corresponding effect-size metric', async () => {
    const onChange = vi.fn()
    render(<PowerWizard spec={baseSpec} onChange={onChange} />)

    await userEvent.selectOptions(
      screen.getByLabelText(/设计类型/),
      't_test',
    )

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      designFamily: 't_test',
      effectSize: { metric: 'cohens_d', value: 0.15 },
    }))
  })
})
