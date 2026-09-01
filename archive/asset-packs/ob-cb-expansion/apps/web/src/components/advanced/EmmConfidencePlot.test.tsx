import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EmmConfidencePlot } from './EmmConfidencePlot'

describe('EmmConfidencePlot', () => {
  it('renders only model-based EMM values and exposes exact intervals accessibly', () => {
    render(
      <EmmConfidencePlot
        rows={[
          { treatment: 'A', phase: 'pre', emmean: 4.25, SE: 0.4, df: 13, 'lower.CL': 3.39, 'upper.CL': 5.11 },
          { treatment: 'B', phase: 'pre', emmean: 6.5, SE: 0.5, df: 13, 'lower.CL': 5.42, 'upper.CL': 7.58 },
        ]}
      />,
    )

    expect(screen.getByRole('img', { name: /^Estimated marginal means and confidence intervals/ })).toBeInTheDocument()
    expect(screen.getByText('treatment=A, phase=pre')).toBeInTheDocument()
    expect(screen.getByText('treatment=B, phase=pre')).toBeInTheDocument()
    expect(screen.getByText(/组间判断应使用 contrast 表/)).toBeInTheDocument()
  })

  it('does not invent a chart when confidence limits are unavailable', () => {
    const { container } = render(<EmmConfidencePlot rows={[{ treatment: 'A', emmean: 4.25 }]} />)
    expect(container).toBeEmptyDOMElement()
  })
})
