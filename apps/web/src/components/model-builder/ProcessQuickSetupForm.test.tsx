import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ModelSpec, ModelVariable } from '../../types'
import { ProcessQuickSetupForm } from './ProcessQuickSetupForm'

const variables: ModelVariable[] = ['x', 'm', 'w', 'y'].map((id) => ({
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

    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('中介变量 M'), { target: { value: 'm' } })
    fireEvent.change(screen.getByLabelText('Bootstrap 次数'), { target: { value: '8000' } })
    fireEvent.click(screen.getByRole('button', { name: '应用并进入复核' }))

    expect(onApply).toHaveBeenCalledWith({
      kind: 'mediation',
      xVariableId: 'x',
      yVariableId: 'y',
      mediatorVariableId: 'm',
      moderatorVariableId: undefined,
      confidenceLevel: 0.95,
      bootstrapReplicates: 8000,
      meanCenterPredictors: false,
    })
  })

  it('switches to moderation and exposes W plus centering', () => {
    const onApply = vi.fn(() => true)
    render(
      <ProcessQuickSetupForm variables={variables} model={model} onApply={onApply} onOpenAdvanced={vi.fn()} />,
    )

    fireEvent.click(screen.getByRole('button', { name: '简单调节 · Model 1' }))
    expect(screen.queryByLabelText('中介变量 M')).not.toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('自变量 X'), { target: { value: 'x' } })
    fireEvent.change(screen.getByLabelText('结果变量 Y'), { target: { value: 'y' } })
    fireEvent.change(screen.getByLabelText('调节变量 W'), { target: { value: 'w' } })
    fireEvent.click(screen.getByLabelText('对 X 与 W 做均值中心化'))
    fireEvent.click(screen.getByRole('button', { name: '应用并进入复核' }))

    expect(onApply).toHaveBeenCalledWith(expect.objectContaining({
      kind: 'moderation',
      xVariableId: 'x',
      yVariableId: 'y',
      moderatorVariableId: 'w',
      meanCenterPredictors: true,
    }))
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
    expect(screen.getByRole('button', { name: '应用并进入复核' })).toBeDisabled()
    expect(onApply).not.toHaveBeenCalled()
  })
})
