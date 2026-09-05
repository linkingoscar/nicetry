import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ModelSpec, ModelVariable } from '../../types'
import { ProcessQuickSetupForm } from './ProcessQuickSetupForm'

const variables: ModelVariable[] = ['x', 'm', 'm2', 'w', 'y'].map((id) => ({
  id,
  label: id.toUpperCase(),
  kind: 'observed',
  dataType: 'continuous',
  source: id,
  encodingHint: { method: 'as_is', label: '原值', reason: 'test' },
}))

const model = {
  nodes: [],
  estimation: {
    confidenceLevel: 0.95,
    bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 1 },
    centering: { method: 'none', nodeIds: [] },
  },
} as unknown as ModelSpec

describe('ProcessQuickSetupForm', () => {
  it('collects a simple mediation setup without running anything', () => {
    const onApply = vi.fn(() => true)
    render(
      <ProcessQuickSetupForm variables={variables} model={model} onApply={onApply} onOpenAdvanced={vi.fn()} />,
    )

    expect(screen.getByRole('heading', { name: '简单中介 · PROCESS Model 4' })).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('中介变量 M'), { target: { value: 'm' } })
    fireEvent.change(screen.getByLabelText('Bootstrap 次数'), { target: { value: '8000' } })
    fireEvent.click(screen.getByRole('button', { name: '应用表单设置' }))

    expect(onApply).toHaveBeenCalledWith({
      kind: 'mediation',
      xVariableId: 'x',
      yVariableId: 'y',
      mediatorVariableId: 'm',
      secondMediatorVariableId: undefined,
      moderatorVariableId: undefined,
      confidenceLevel: 0.95,
      bootstrapReplicates: 8000,
      meanCenterPredictors: false,
    })
  })

  it('keeps serial mediation method-scoped and collects M1/M2 without a second model chooser', () => {
    const onApply = vi.fn(() => true)
    render(
      <ProcessQuickSetupForm
        variables={variables}
        model={model}
        initialKind="serial_mediation"
        onApply={onApply}
        onOpenAdvanced={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: '链式中介 · PROCESS Model 6' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /简单中介/ })).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('中介变量 M1'), { target: { value: 'm' } })
    fireEvent.change(screen.getByLabelText('中介变量 M2'), { target: { value: 'm2' } })
    fireEvent.click(screen.getByRole('button', { name: '应用表单设置' }))

    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'serial_mediation',
      mediatorVariableId: 'm',
      secondMediatorVariableId: 'm2',
    }))
  })

  it('exposes X/W centering for first-stage moderated mediation', () => {
    const onApply = vi.fn(() => true)
    render(
      <ProcessQuickSetupForm
        variables={variables}
        model={model}
        initialKind="moderated_mediation_first"
        onApply={onApply}
        onOpenAdvanced={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: '第一阶段调节中介 · PROCESS Model 7' })).toBeInTheDocument()
    expect(screen.getByLabelText('对 X 与 W 做均值中心化')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('中介变量 M'), { target: { value: 'm' } })
    fireEvent.change(screen.getByLabelText('调节变量 W'), { target: { value: 'w' } })
    fireEvent.click(screen.getByLabelText('对 X 与 W 做均值中心化'))
    fireEvent.click(screen.getByRole('button', { name: '应用表单设置' }))

    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'moderated_mediation_first',
      moderatorVariableId: 'w',
      meanCenterPredictors: true,
    }))
  })

  it('labels M/W centering for second-stage moderated mediation', () => {
    render(
      <ProcessQuickSetupForm
        variables={variables}
        model={model}
        initialKind="moderated_mediation_second"
        onApply={vi.fn(() => true)}
        onOpenAdvanced={vi.fn()}
      />,
    )

    expect(screen.getByRole('heading', { name: '第二阶段调节中介 · PROCESS Model 14' })).toBeInTheDocument()
    expect(screen.getByLabelText('对 M 与 W 做均值中心化')).toBeInTheDocument()
    expect(screen.queryByLabelText('对 X 与 W 做均值中心化')).not.toBeInTheDocument()
  })

  it('prevents overlapping role assignments', () => {
    const onApply = vi.fn(() => true)
    render(
      <ProcessQuickSetupForm variables={variables} model={model} onApply={onApply} onOpenAdvanced={vi.fn()} />,
    )

    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('中介变量 M'), { target: { value: 'x' } })

    expect(screen.getByText(/必须使用不同变量/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '应用表单设置' })).toBeDisabled()
    expect(onApply).not.toHaveBeenCalled()
  })

  it('keeps the advanced editor as an explicit optional path', () => {
    const onOpenAdvanced = vi.fn()
    render(
      <ProcessQuickSetupForm variables={variables} model={model} onApply={vi.fn(() => true)} onOpenAdvanced={onOpenAdvanced} />,
    )

    fireEvent.click(screen.getByRole('button', { name: '打开高级编辑器' }))
    expect(onOpenAdvanced).toHaveBeenCalledTimes(1)
  })
})
