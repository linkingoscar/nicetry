import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { MultilevelWizard, type MultilevelWizardSpec } from './MultilevelWizard'

const spec: MultilevelWizardSpec = {
  family: 'multilevel_model',
  analysisType: 'lmm',
  outcomeId: 'outcome',
  distribution: 'gaussian',
  clusterVariableId: '',
  fixedEffectIds: ['predictor'],
  randomEffects: [],
  centering: [],
  estimator: 'REML',
  degreesOfFreedom: 'satterthwaite',
  minimumClusterCount: 30,
  scaleItemIds: [],
  scaleMin: 1,
  scaleMax: 5,
  aggregationMethod: 'mean',
}

const variables = [
  { id: 'outcome', name: 'outcome', label: '结果', type: 'numeric' as const },
  { id: 'predictor', name: 'predictor', label: '预测', type: 'numeric' as const },
  { id: 'team_id', name: 'team_id', label: '团队 ID', type: 'text' as const },
]

describe('MultilevelWizard', () => {
  it('requires an explicit cluster role and creates a random intercept', async () => {
    const onChange = vi.fn()
    render(<MultilevelWizard spec={spec} onChange={onChange} variables={variables} />)

    await userEvent.selectOptions(screen.getByLabelText(/Cluster ID/), 'team_id')

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      clusterVariableId: 'team_id',
      randomEffects: [expect.objectContaining({
        groupingVariableId: 'team_id',
        intercept: true,
      })],
    }))
    expect(screen.getByText(/三层、交叉分类与广义结局暂不开放/)).toBeInTheDocument()
  })
})
