import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { MultilevelWizard, multilevelAnalysisTypeForSlice, type MultilevelWizardSpec } from './MultilevelWizard'

vi.mock('./DatasetVariablePicker', () => ({
  DatasetVariablePicker: ({ label }: { label: string }) => <div>{label}</div>,
}))

const variables = [
  { id: 'cluster', name: 'cluster', label: 'Cluster', type: 'categorical', recommendedRoles: ['cluster'] },
  { id: 'outcome', name: 'outcome', label: 'Outcome', type: 'numeric' },
  { id: 'x', name: 'x', label: 'X', type: 'numeric' },
  { id: 'item_1', name: 'item_1', label: 'Item 1', type: 'numeric' },
  { id: 'item_2', name: 'item_2', label: 'Item 2', type: 'numeric' },
] as never[]

const baseSpec: MultilevelWizardSpec = {
  family: 'multilevel_model',
  analysisType: 'lmm',
  outcomeId: 'outcome',
  distribution: 'gaussian',
  clusterVariableId: 'cluster',
  fixedEffectIds: ['x'],
  randomEffects: [{ groupingVariableId: 'cluster', intercept: true, slopeVariableIds: [], covariance: 'correlated' }],
  centering: [],
  estimator: 'REML',
  degreesOfFreedom: 'satterthwaite',
  minimumClusterCount: 30,
  scaleItemIds: ['item_1', 'item_2'],
  scaleMin: 1,
  scaleMax: 5,
  aggregationMethod: 'mean',
}

describe('MultilevelWizard method-scoped forms', () => {
  it('maps registered slices to one locked analysis type', () => {
    expect(multilevelAnalysisTypeForSlice('multilevel_model.aggregation.icc_rwg')).toBe('aggregation')
    expect(multilevelAnalysisTypeForSlice('multilevel_model.gaussian.two_level')).toBe('lmm')
  })

  it('shows only aggregation settings for the ICC method even if the draft says lmm', () => {
    render(
      <MultilevelWizard
        spec={{ ...baseSpec, analysisType: 'lmm' }}
        onChange={vi.fn()}
        variables={variables}
        sliceId="multilevel_model.aggregation.icc_rwg"
      />,
    )

    expect(screen.getByRole('heading', { name: 'ICC 与聚合诊断' })).toBeInTheDocument()
    expect(screen.getByText('构成团队层构念的题项')).toBeInTheDocument()
    expect(screen.queryByLabelText('结果变量')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('自由度近似')).not.toBeInTheDocument()
  })

  it('shows LMM inference and centering controls for the gaussian method', () => {
    render(
      <MultilevelWizard
        spec={{ ...baseSpec, analysisType: 'aggregation' }}
        onChange={vi.fn()}
        variables={variables}
        sliceId="multilevel_model.gaussian.two_level"
      />,
    )

    expect(screen.getByRole('heading', { name: '两层 Gaussian LMM' })).toBeInTheDocument()
    expect(screen.getByLabelText('结果变量')).toBeInTheDocument()
    expect(screen.getByLabelText('自由度近似')).toBeInTheDocument()
    expect(screen.getByText('连续预测变量中心化')).toBeInTheDocument()
    expect(screen.queryByText('构成团队层构念的题项')).not.toBeInTheDocument()
  })
})
