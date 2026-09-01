import { fireEvent, render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ModelSpec } from '../../types'
import { ModerationEditor } from './ModerationEditor'

const model: ModelSpec = {
  schemaVersion: '1.0.0',
  modelId: 'model_custom_test',
  name: '自定义条件过程模型',
  datasetVersionId: 'derived_test',
  design: {
    timeStructure: 'cross_sectional',
    clustering: 'none',
    claimMode: 'associational',
  },
  nodes: [
    { id: 'node_x', variableId: 'var_x', label: 'X', kind: 'observed', role: 'x', dataType: 'continuous' },
    { id: 'node_m', variableId: 'var_m', label: 'M', kind: 'observed', role: 'm', dataType: 'continuous' },
    { id: 'node_y', variableId: 'var_y', label: 'Y', kind: 'observed', role: 'y', dataType: 'continuous' },
    { id: 'node_w', variableId: 'var_w', label: 'W', kind: 'observed', role: 'w', dataType: 'continuous' },
    { id: 'node_z', variableId: 'var_z', label: 'Z', kind: 'observed', role: 'z', dataType: 'continuous' },
  ],
  edges: [
    { id: 'edge_x_m', from: 'node_x', to: 'node_m', kind: 'regression' },
    { id: 'edge_m_y', from: 'node_m', to: 'node_y', kind: 'regression' },
    { id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression' },
  ],
  moderations: [],
  covariates: [],
  estimation: {
    family: 'ols',
    standardErrors: 'hc3',
    confidenceLevel: 0.95,
    bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 20250730 },
    missing: 'complete_cases_per_model',
    centering: { method: 'none', nodeIds: [] },
    reportScale: 'unstandardized_primary',
  },
}

describe('ModerationEditor PROCESS 5.0 manual map', () => {
  it('binds W, Z, and W×Z to an explicitly selected path', () => {
    const onChange = vi.fn()
    render(<ModerationEditor model={model} onChange={onChange} />)
    const manualMap = screen.getByRole('group', { name: /自由构建/ })
    const firstPath = within(manualMap).getByText('X→M').closest<HTMLElement>('.manual-moderation-row')
    if (!firstPath) throw new Error('未找到 X→M 手动调节行')

    fireEvent.click(within(firstPath).getByRole('button', { name: 'W' }))
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({
        moderatorNodeId: 'node_w',
        targetEdgeId: 'edge_x_m',
      }),
    ])

    fireEvent.click(within(firstPath).getByRole('button', { name: 'W×Z' }))
    expect(onChange).toHaveBeenLastCalledWith([
      expect.objectContaining({
        moderatorNodeId: 'node_w',
        secondaryModeratorNodeId: 'node_z',
        targetEdgeId: 'edge_x_m',
      }),
    ])
  })
})
