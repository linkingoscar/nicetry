import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { DatasetVersion, ModelSpec, ModelVariable } from '../../types'
import { SemStudio } from './SemStudio'
import { ModelEstimationEditor } from './ModelEstimationEditor'

const baseModel: ModelSpec = {
  schemaVersion: '0.3.0',
  modelId: 'sem_studio_test',
  name: 'SEM Studio',
  datasetVersionId: 'dataset_version_test',
  design: {
    timeStructure: 'cross_sectional',
    clustering: 'none',
    claimMode: 'associational',
  },
  nodes: [],
  edges: [],
  moderations: [],
  covariates: [],
  latents: [
    { id: 'factor_one', name: '构念一', level: 'first_order', indicators: ['item_one', 'item_two'] },
    { id: 'factor_two', name: '构念二', level: 'first_order', indicators: ['item_three', 'item_four'] },
    { id: 'factor_three', name: '构念三', level: 'first_order', indicators: ['item_five', 'item_six'] },
  ],
  estimation: {
    family: 'sem',
    estimator: 'ML',
    groupVariableId: 'group_variable',
    invariance: false,
    standardErrors: 'standard',
    confidenceLevel: 0.95,
    bootstrap: { enabled: false, replicates: 1000, method: 'percentile', seed: 12345 },
    missing: 'fiml',
    centering: { method: 'none', nodeIds: [] },
    reportScale: 'unstandardized_primary',
  },
}

const variables = [
  {
    id: 'group_variable',
    label: '组别',
    kind: 'observed',
    dataType: 'binary',
    source: 'group',
    encodingHint: { method: 'binary_indicator', label: '二分类', reason: '测试' },
  },
] as ModelVariable[]

const indicators = [
  { id: 'item_one', label: '题项 1', originalName: 'item1' },
  { id: 'item_two', label: '题项 2', originalName: 'item2' },
  { id: 'item_three', label: '题项 3', originalName: 'item3' },
  { id: 'item_four', label: '题项 4', originalName: 'item4' },
  { id: 'item_five', label: '题项 5', originalName: 'item5' },
  { id: 'item_six', label: '题项 6', originalName: 'item6' },
] as DatasetVersion['variables']

function StudioHarness() {
  const [model, setModel] = useState(baseModel)
  return (
    <SemStudio
      model={model}
      variables={variables}
      indicatorCandidates={indicators}
      updateModel={(updater) => setModel((current) => updater(current))}
    />
  )
}

describe('SemStudio', () => {
  it('leaves same-family settings intact and confirms before discarding custom SEM settings', () => {
    const switchFamily = vi.fn()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const model = { ...baseModel, latents: [...(baseModel.latents ?? []), { id: 'higher', name: '总体构念', level: 'higher_order' as const, indicators: ['factor_one', 'factor_two', 'factor_three'] }] }
    const view = render(<ModelEstimationEditor model={model} variables={variables} indicatorCandidates={indicators} updateModel={vi.fn()} onSwitchEstimationFamily={switchFamily} />)
    fireEvent.click(screen.getByRole('button', { name: 'lavaan (SEM 结构方程)' }))
    expect(confirm).not.toHaveBeenCalled()
    expect(switchFamily).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'PROCESS (OLS 回归)' }))
    expect(confirm).toHaveBeenCalledWith(expect.stringContaining('高阶因子'))
    expect(switchFamily).not.toHaveBeenCalled()
    confirm.mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', { name: 'PROCESS (OLS 回归)' }))
    expect(switchFamily).toHaveBeenCalledWith('ols')
    expect(model.estimation.groupVariableId).toBe('group_variable')
    expect(model.latents).toHaveLength(4)
    view.unmount()
    confirm.mockRestore()
  })
  it('builds a higher-order factor and exposes multi-group comparisons', () => {
    render(<StudioHarness />)

    fireEvent.click(screen.getByRole('button', { name: '添加高阶潜变量' }))
    expect(screen.getByText(/总体构念 · 3 个低阶因子 · 高阶/)).toBeInTheDocument()

    fireEvent.click(screen.getByLabelText(/逐级测量等值性/))
    fireEvent.click(screen.getByLabelText('比较结构路径等值模型'))
    fireEvent.click(screen.getByLabelText('在截距/阈值等值模型中估计潜均值'))
    fireEvent.change(screen.getByLabelText(/理论或探索性理由/), {
      target: { value: '该题项存在预设的组间措辞差异。' },
    })
    fireEvent.click(screen.getByRole('button', { name: '添加手动释放' }))

    expect(screen.getByLabelText('比较结构路径等值模型')).toBeChecked()
    expect(screen.getByLabelText('在截距/阈值等值模型中估计潜均值')).toBeChecked()
    expect(screen.getByText(/metric · loading · 题项 1/)).toBeInTheDocument()
  })
})
