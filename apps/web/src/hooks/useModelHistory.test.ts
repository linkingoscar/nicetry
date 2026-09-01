import { act, renderHook } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { ModelSpec } from '../types'
import { useModelHistory } from './useModelHistory'

const snapshot = (name: string) => ({ name } as ModelSpec)

describe('model undo history', () => {
  it('retains previous snapshots across batched edits and reversible undo/redo', () => {
    const original = snapshot('initial')
    const first = snapshot('first')
    const second = snapshot('second')
    const { result } = renderHook(() => useModelHistory(original))
    act(() => { result.current.pushState(first); result.current.pushState(second) })
    act(() => { expect(result.current.undo()).toEqual(first) })
    act(() => { expect(result.current.undo()).toEqual(original) })
    expect(result.current.canUndo).toBe(false)
    act(() => { expect(result.current.redo()).toEqual(first) })
    act(() => { expect(result.current.redo()).toEqual(second) })
    expect(result.current.canRedo).toBe(false)
  })

  it('starts history at the hydrated draft and discards redo after a new edit', () => {
    const loaded = snapshot('loaded draft')
    const { result } = renderHook(() => useModelHistory(snapshot('template')))
    act(() => { result.current.resetHistory(loaded) })
    act(() => { result.current.pushState(snapshot('edit')) })
    act(() => { expect(result.current.undo()).toEqual(loaded) })
    act(() => { result.current.pushState(snapshot('new branch')) })
    expect(result.current.canRedo).toBe(false)
    act(() => { expect(result.current.undo()).toEqual(loaded) })
  })
})
