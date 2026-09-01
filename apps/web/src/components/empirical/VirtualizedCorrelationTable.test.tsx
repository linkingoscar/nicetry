import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { VirtualizedCorrelationTable } from './VirtualizedCorrelationTable'

vi.mock('@tanstack/react-virtual', () => ({
  useVirtualizer: (options: { count: number; horizontal?: boolean }) => {
    const visibleCount = Math.min(options.count, options.horizontal ? 9 : 11)
    const size = options.horizontal ? 75 : 38
    return {
      getVirtualItems: () => Array.from({ length: visibleCount }, (_, index) => ({
        index,
        start: index * size,
        size,
      })),
      getTotalSize: () => options.count * size,
    }
  },
}))

describe('VirtualizedCorrelationTable', () => {
  it.each([0.9, 0.95, 0.99])('does not mark self-correlation significant and labels %s intervals', (confidenceLevel) => {
    render(<VirtualizedCorrelationTable variables={[{ id: 'a', label: 'A' }, { id: 'b', label: 'B' }]}
      coefficients={[[1, 0.4], [0.4, 1]]} pValues={[[0, 0.01], [0.01, 0]]} counts={[[50, 50], [50, 50]]}
      ciLower={[[null, 0.2], [0.2, null]]} ciUpper={[[null, 0.6], [0.6, null]]} confidenceLevel={confidenceLevel}
      metric={(v) => String(v)} significance={() => '**'} />)
    expect(screen.getAllByRole('cell', { name: '1' })).toHaveLength(2)
    expect(screen.getByRole('cell', { name: '0.4**' })).toHaveAttribute('title', `N=50；${Math.round(confidenceLevel * 100)}% CI [0.2, 0.6]`)
  })

  it('keeps a 200 by 200 matrix within the viewport DOM budget', () => {
    const size = 200
    const variables = Array.from({ length: size }, (_, index) => ({
      id: `v${index + 1}`,
      label: `V${index + 1}`,
    }))
    const coefficients = Array.from({ length: size }, () => Array<number | null>(size).fill(0.5))
    const pValues = Array.from({ length: size }, () => Array<number | null>(size).fill(0.01))
    const counts = Array.from({ length: size }, () => Array<number>(size).fill(500))
    const ciLower = Array.from({ length: size }, () => Array<number | null>(size).fill(0.4))
    const ciUpper = Array.from({ length: size }, () => Array<number | null>(size).fill(0.6))

    render(
      <VirtualizedCorrelationTable
        variables={variables}
        coefficients={coefficients}
        pValues={pValues}
        counts={counts}
        ciLower={ciLower}
        ciUpper={ciUpper}
        metric={(value) => String(value)}
        significance={() => '*'}
      />,
    )

    const table = screen.getByRole('table', { name: '相关矩阵' })
    expect(table).toHaveAttribute('aria-rowcount', '201')
    expect(table).toHaveAttribute('aria-colcount', '201')
    expect(screen.getAllByRole('cell')).toHaveLength(80)
    expect(screen.getByRole('rowheader', { name: '1. V1' })).toBeInTheDocument()
    expect(screen.queryByRole('rowheader', { name: '200. V200' })).not.toBeInTheDocument()
  })
})
