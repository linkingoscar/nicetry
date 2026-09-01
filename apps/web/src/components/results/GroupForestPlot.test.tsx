import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { InvarianceResult } from '../../types'
import { GroupForestPlot } from './GroupForestPlot'

const resultWithoutConfidenceInterval: InvarianceResult = {
  groupParameters: [
    {
      group: 'A',
      loadings: [],
      paths: [
        {
          from: 'X',
          to: 'Y',
          estimate: 0.2,
          standardError: 0.1,
          pValue: 0.2,
          stdAll: 0.2,
        },
      ],
    },
  ],
  pathComparisons: [],
  models: [],
  comparisons: [],
}

describe('GroupForestPlot', () => {
  it('does not invent a confidence interval when the backend omits it', () => {
    render(<GroupForestPlot invarianceResult={resultWithoutConfidenceInterval} />)

    expect(screen.getByText('B=0.200 [CI 不可用]')).toBeInTheDocument()
    expect(screen.queryByText(/\[0\.20, 0\.20\]/)).not.toBeInTheDocument()
  })
})
