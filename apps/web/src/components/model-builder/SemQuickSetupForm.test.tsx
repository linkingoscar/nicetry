import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { MeasurementVersion, ModelSpec } from '../../types'
import { SemQuickSetupForm } from './SemQuickSetupForm'

const measurement = {
  constructs: [
    { id: 'cx', name: 'Predictor', outputVariableId: 'score_x' },
    { id: 'cy', name: 'Outcome', outputVariableId: 'score_y' },
  ],
} as unknown as MeasurementVersion

const model = {
  estimation: {
    estimator: 'ML',
    confidenceLevel: 0.95,
    missing: 'fiml',
  },
} as ModelSpec

describe('SemQuickSetupForm', () => {
  it('collects the basic X→Y latent path and ML options without running', () => {
    const onApply = vi.fn(() => true)
    render(<SemQuickSetupForm measurement={measurement} model={model} onApply={onApply} onOpenAdvanced={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('置信水平'), { target: { value: '0.99' } })
    fireEvent.click(screen.getByRole('button', { name: '应用 SEM 设置' }))

    expect(onApply).toHaveBeenCalledWith({
      predictorVariableId: 'score_x',
      outcomeVariableId: 'score_y',
      estimator: 'ML',
      confidenceLevel: 0.99,
      missing: 'fiml',
    })
  })

  it('forces complete-case handling when WLSMV is selected', () => {
    const onApply = vi.fn(() => true)
    render(<SemQuickSetupForm measurement={measurement} model={model} onApply={onApply} onOpenAdvanced={vi.fn()} />)

    fireEvent.change(screen.getByLabelText('估计器'), { target: { value: 'WLSMV' } })
    expect(screen.queryByLabelText('缺失数据')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '应用 SEM 设置' }))

    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({
      estimator: 'WLSMV',
      missing: 'complete_cases_per_model',
    }))
  })

  it('blocks setup when fewer than two constructs exist', () => {
    const oneConstruct = { constructs: [measurement.constructs[0]] } as unknown as MeasurementVersion
    render(<SemQuickSetupForm measurement={oneConstruct} model={model} onApply={vi.fn(() => true)} onOpenAdvanced={vi.fn()} />)

    expect(screen.getByText(/至少需要两个已定义构念/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '应用 SEM 设置' })).toBeDisabled()
  })
})
