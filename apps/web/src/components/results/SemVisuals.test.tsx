import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { InvarianceResult } from '../../types'
import { ModelImpliedPredictionPlot } from './ModelImpliedPredictionPlot'
import { PathCoefficientForestPlot } from './PathCoefficientForestPlot'

const groups: NonNullable<InvarianceResult['groupParameters']> = [
  {
    group: 'A',
    loadings: [],
    paths: [
      {
        from: 'X',
        to: 'Y',
        estimate: 0.4,
        standardError: 0.1,
        pValue: 0.001,
        stdAll: 0.35,
        ciLower: 0.2,
        ciUpper: 0.6,
      },
    ],
  },
  {
    group: 'B',
    loadings: [],
    paths: [
      {
        from: 'X',
        to: 'Y',
        estimate: -0.1,
        standardError: 0.12,
        pValue: 0.4,
        stdAll: -0.08,
        ciLower: -0.34,
        ciUpper: 0.14,
      },
    ],
  },
]

const prediction: NonNullable<InvarianceResult['predictionPlots']>[number] = {
  from: 'X',
  to: 'Y',
  predictorLabel: 'X',
  outcomeLabel: 'Y',
  confidenceLevel: 0.95,
  method: 'Model-implied observed-scale line',
  groups: [
    {
      group: 'A',
      xValues: [0, 1, 2],
      predictedValues: [0, 0.4, 0.8],
      ciLower: [-0.1, 0.25, 0.55],
      ciUpper: [0.1, 0.55, 1.05],
    },
    {
      group: 'B',
      xValues: [0, 1, 2],
      predictedValues: [0.5, 0.4, 0.3],
      ciLower: [0.35, 0.2, 0.05],
      ciUpper: [0.65, 0.6, 0.55],
    },
  ],
}

describe('SEM multi-group visuals', () => {
  it('renders uncertainty-aware forest and eligible prediction plots', () => {
    render(
      <>
        <PathCoefficientForestPlot groups={groups} />
        <ModelImpliedPredictionPlot plot={prediction} />
      </>,
    )

    expect(screen.getByRole('img', { name: '各组结构路径系数森林图' })).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Y 对 X 的多组模型隐含预测线' })).toBeInTheDocument()
    expect(screen.getByText(/未标准化 B/)).toBeInTheDocument()
    expect(screen.getByText(/观测尺度、单一预测方程/)).toBeInTheDocument()
    expect(screen.getByText('95% CI [.200, .600]')).toBeInTheDocument()
  })

  it('does not invent missing group paths or Wald intervals when uncertainty is unavailable', () => {
    const sparseGroups: NonNullable<InvarianceResult['groupParameters']> = [
      {
        ...groups[0],
        paths: [
          ...groups[0].paths,
          {
            from: 'M',
            to: 'Y',
            estimate: 0.25,
            standardError: null,
            pValue: null,
            stdAll: 0.2,
            ciLower: null,
            ciUpper: null,
          },
        ],
      },
      groups[1],
    ]

    render(<PathCoefficientForestPlot groups={sparseGroups} />)

    const detailsTable = screen.getByRole('table', { name: '路径系数森林图数据明细表' })
    expect(within(detailsTable).getAllByRole('row')).toHaveLength(4)
    expect(within(detailsTable).getAllByText('M → Y')).toHaveLength(1)
    expect(within(detailsTable).getAllByText('—')).toHaveLength(3)
  })
})
