import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CorrelationHeatmap } from './CorrelationHeatmap'
import { EmpiricalCorrelationTab } from './EmpiricalCorrelationTab'

vi.mock('./VirtualizedCorrelationTable', () => ({ VirtualizedCorrelationTable: () => null }))

const variables = [{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]
const coefficients = [[1, -1], [-1, 1]]

describe('correlation presentation', () => {
  it('matches signed legend colors to cells when the palette changes and suppresses diagonal stars', () => {
    render(<CorrelationHeatmap variables={variables} coefficients={coefficients} pValues={[[0, 0.001], [0.001, 0]]} />)
    const positive = screen.getByText(/正相关/).querySelector('span')
    const negative = screen.getByText(/负相关/).querySelector('span')
    expect(positive).toHaveStyle({ background: 'rgb(213, 94, 0)' })
    expect(negative).toHaveStyle({ background: 'rgb(86, 180, 233)' })
    expect(screen.getByRole('img').querySelectorAll('rect')[0]).toHaveAttribute('fill', 'rgb(213, 94, 0)')
    fireEvent.click(screen.getByRole('button', { name: 'Viridis' }))
    expect(positive).toHaveStyle({ background: 'rgb(253, 231, 37)' })
    expect(negative).toHaveStyle({ background: 'rgb(68, 1, 84)' })
    const cells = within(screen.getByRole('table', { hidden: true })).getAllByRole('cell', { hidden: true })
    expect(cells[0]).not.toHaveTextContent('*')
    expect(cells[2]).toHaveTextContent('**')
    expect(cells[3]).not.toHaveTextContent('*')
  })

  it.each([0.9, 0.95, 0.99])('reads the %s interval level from the persisted result', (confidenceLevel) => {
    render(<EmpiricalCorrelationTab reportOptions={{ correlationMethod: 'pearson' }} query={{
      isLoading: false, isError: false, error: null,
      data: { correlations: { variables, coefficients, pValues: [[0, 0.01], [0.01, 0]], counts: [[50, 50], [50, 50]], confidenceLevel, method: 'pearson' } },
    }} />)
    expect(screen.getByText(new RegExp(`${Math.round(confidenceLevel * 100)}% CI 为单个区间`))).toBeInTheDocument()
  })
})
