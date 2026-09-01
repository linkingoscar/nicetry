import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { PaperReadySummaryTable } from './PaperReadySummaryTable'

describe('PaperReadySummaryTable', () => {
  it('presents a descriptive summary without a publication-ready claim', () => {
    render(
      <PaperReadySummaryTable
        table={{
          title: 'Descriptive statistics, reliability, and correlations',
          correlationMethod: 'Pearson',
          confidenceLevel: 0.9,
          variables: [{ id: 'x', label: 'X' }],
          rows: [
            {
              id: 'x',
              label: 'X',
              n: 10,
              mean: 1,
              sd: 2,
              alpha: null,
              omega: null,
              correlations: [1],
              pValues: [null],
              counts: [10],
              ciLower: [1],
              ciUpper: [1],
            },
          ],
        }}
        metric={(value) => (value === null || value === undefined ? '—' : String(value))}
        significance={() => ''}
      />,
    )

    expect(screen.getByText('Descriptive summary')).toBeInTheDocument()
    expect(screen.queryByText('Paper-ready table')).not.toBeInTheDocument()
    expect(screen.getByText(/不声明 publicationEligible/)).toBeInTheDocument()
    expect(screen.getByText(/90% CI/)).toBeInTheDocument()
  })
})
