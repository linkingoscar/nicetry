import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MethodResultVisuals } from './MethodResultVisuals'

describe('MethodResultVisuals', () => {
  it('renders a power sensitivity curve only when enough source points exist', () => {
    const { rerender } = render(
      <MethodResultVisuals familyResult={{ family: 'power_analysis', powerCurve: [{ sampleSize: 80, power: .63 }] }} />,
    )
    expect(screen.queryByRole('img', { name: '功效与样本量敏感性' })).not.toBeInTheDocument()

    rerender(
      <MethodResultVisuals
        familyResult={{
          family: 'power_analysis',
          powerCurve: [
            { sampleSize: 80, power: .63 },
            { sampleSize: 120, power: .82 },
          ],
        }}
      />,
    )
    expect(screen.getByRole('img', { name: '功效与样本量敏感性' })).toBeInTheDocument()
  })

  it('renders questionnaire diagnostics from actual returned item evidence', () => {
    render(
      <MethodResultVisuals
        familyResult={{
          family: 'questionnaire_measurement',
          bifactor: { bifactorMetrics: { omegaH: .73, ecv: .61 } },
          irt: {
            itemParameters: [{ itemId: 'q1', discrimination: 1.4 }],
            difAnalysis: [{ itemId: 'q2', effectSize: .08 }],
          },
        }}
      />,
    )
    expect(screen.getByText('Bifactor 核心诊断')).toBeInTheDocument()
    expect(screen.getByText('IRT 区分度概览')).toBeInTheDocument()
    expect(screen.getByText('DIF 效应筛查')).toBeInTheDocument()
  })
})
