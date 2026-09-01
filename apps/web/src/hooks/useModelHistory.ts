import { useCallback, useRef, useState } from 'react'
import type { ModelSpec } from '../types'

export function useModelHistory(initialModel: ModelSpec) {
  const [past, setPast] = useState<ModelSpec[]>([])
  const [future, setFuture] = useState<ModelSpec[]>([])
  const currentRef = useRef<ModelSpec>(initialModel)

  const pushState = useCallback((nextModel: ModelSpec) => {
    // 如果与当前状态 JSON 一致，则无需推入
    if (JSON.stringify(currentRef.current) === JSON.stringify(nextModel)) return
    const previousModel = currentRef.current
    setPast((prev) => [...prev.slice(-25), previousModel])
    currentRef.current = nextModel
    setFuture([])
  }, [])

  const undo = useCallback((): ModelSpec | null => {
    if (past.length === 0) return null
    const previous = past[past.length - 1]
    const newPast = past.slice(0, past.length - 1)
    const currentModel = currentRef.current
    setFuture((prev) => [currentModel, ...prev])
    setPast(newPast)
    currentRef.current = previous
    return previous
  }, [past])

  const redo = useCallback((): ModelSpec | null => {
    if (future.length === 0) return null
    const next = future[0]
    const newFuture = future.slice(1)
    const currentModel = currentRef.current
    setPast((prev) => [...prev, currentModel])
    setFuture(newFuture)
    currentRef.current = next
    return next
  }, [future])

  const resetHistory = useCallback((newModel: ModelSpec) => {
    currentRef.current = newModel
    setPast([])
    setFuture([])
  }, [])

  return {
    pushState,
    undo,
    redo,
    resetHistory,
    canUndo: past.length > 0,
    canRedo: future.length > 0,
  }
}
