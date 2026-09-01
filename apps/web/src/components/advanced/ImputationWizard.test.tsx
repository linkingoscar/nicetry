import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ImputationWizard, type ImputationWizardSpec } from './ImputationWizard'

const variables = [
  { id: 'y', name: 'y', label: '结果 Y', type: 'numeric' as const, missingRate: 0 },
  { id: 'x', name: 'x', label: '预测 X', type: 'numeric' as const, missingRate: 0.2 },
  { id: 'z', name: 'z', label: '协变量 Z', type: 'numeric' as const, missingRate: 0 },
]

const spec: ImputationWizardSpec = {
  family: 'multiple_imputation',
  method: 'mice_fcs',
  imputations: 20,
  iterations: 20,
  variables: [{ variableId: 'x', method: 'pmm', predictorIds: ['y'] }],
  pooling: 'rubin',
  pooledAnalysis: {
    modelType: 'linear_regression',
    outcomeId: 'y',
    predictorIds: ['x'],
    includeIntercept: true,
  },
  diagnostics: ['trace', 'distribution'],
}

describe('ImputationWizard', () => {
  it('binds every imputation model to the declared downstream analysis variables', async () => {
    const onChange = vi.fn()
    render(<ImputationWizard spec={spec} onChange={onChange} variables={variables} />)

    await userEvent.selectOptions(screen.getByLabelText(/核心预测变量与协变量/), ['x', 'z'])

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      pooling: 'rubin',
      pooledAnalysis: expect.objectContaining({ outcomeId: 'y', predictorIds: ['x', 'z'] }),
      variables: [expect.objectContaining({ variableId: 'x', predictorIds: ['y', 'z'] })],
    }))
    expect(screen.queryByRole('option', { name: /仅生成插补数据集/ })).not.toBeInTheDocument()
  })
})
