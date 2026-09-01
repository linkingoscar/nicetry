import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type {
  ModelSpec,
  ModelValidation,
} from '../../types'
import { useModelHistory } from '../../hooks/useModelHistory'
import { buildModelVariables, createModelTemplate, templateLabels, type ModelTemplate } from './modelTemplates'
import { buildPathEvidence } from './pathEvidence'
import { restoreActiveRunId } from './runPersistence'
import { createModelCanvasHandlers } from './modelCanvasHandlers'
import { createModelBuilderActions } from './modelBuilderActions'
import { useModelBuilderAnalysis } from './modelBuilderAnalysis'
import { useModelBuilderDrafting, useModelBuilderDraftPersistence } from './modelBuilderDrafting'
import { useModelBuilderKeyboardShortcuts } from './modelBuilderKeyboard'
import type { ModelBuilderState, UseModelBuilderStateOptions } from './modelBuilderStateTypes'

export type { ModelBuilderState } from './modelBuilderStateTypes'

export function useModelBuilderState({
  dataset,
  measurement,
  analysisContext,
}: UseModelBuilderStateOptions): ModelBuilderState {
  const variables = useMemo(() => buildModelVariables(dataset, measurement), [dataset, measurement])
  const indicatorCandidates = useMemo(() => dataset.variables.filter((variable) =>
    ['continuous', 'ordinal', 'likert'].includes(variable.confirmedType ?? variable.inferredType),
  ), [dataset.variables])
  const contextBinding = analysisContext ? {
    contextHash: analysisContext.contextHash,
    sampleVersionId: analysisContext.sample.id,
    sampleHash: analysisContext.sample.hash,
    structureVersionId: analysisContext.structure?.id ?? null,
    structureHash: analysisContext.structure?.hash ?? null,
    measurementVersionId: analysisContext.measurement?.id ?? null,
    measurementHash: analysisContext.measurement?.hash ?? null,
    datasetSha256: analysisContext.dataset.sha256,
  } : {}
  const contextModelId = analysisContext
    ? `model_${dataset.id.slice(-12)}_${analysisContext.contextHash.slice(0, 12)}`
    : `model_${dataset.id.slice(-12)}_pending`
  const previousContextModelId = useRef(contextModelId)
  const bindNewModelContext = (next: ModelSpec): ModelSpec => (
    analysisContext
      ? { ...next, modelId: contextModelId, ...contextBinding }
      : next
  )
  const [template, setTemplate] = useState<ModelTemplate>('model_4')
  const [customMode, setCustomMode] = useState(false)
  const [model, setModel] = useState<ModelSpec>(() => bindNewModelContext(createModelTemplate('model_4', variables, measurement)))
  const { pushState, undo, redo, resetHistory, canUndo, canRedo } = useModelHistory(model)
  const restoreModel = useCallback((restored: ModelSpec) => {
    resetHistory(restored)
    setModel(restored)
  }, [resetHistory])

  const resetModelRef = useRef<(datasetId: string) => ModelSpec>(() => bindNewModelContext(createModelTemplate(template, variables, measurement)))
  resetModelRef.current = (datasetId) => {
    const next = bindNewModelContext(createModelTemplate(template, variables, measurement))
    return analysisContext
      ? { ...next, modelId: `model_${datasetId.slice(-12)}_${analysisContext.contextHash.slice(0, 12)}` }
      : next
  }
  const latestModel = useRef(model)
  latestModel.current = model
  const [validation, setValidation] = useState<ModelValidation | null>(null)
  const [draftState, setDraftState] = useState<'saving' | 'saved' | 'error'>('saving')
  const [overrideReason, setOverrideReason] = useState('')
  const [builderError, setBuilderError] = useState<string | null>(null)
  const [activeRunId, setActiveRunId] = useState<string | null>(() => restoreActiveRunId(dataset.id, model.modelId))
  const [zenMode, setZenMode] = useState(false)
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  const [draftHydrated, setDraftHydrated] = useState(false)
  const contextValue = analysisContext?.studyContext?.value
  const contextGateBlocked = Boolean(
    analysisContext
    && (
      analysisContext.validity !== 'ready'
      || contextValue?.timeStructure !== 'cross_sectional'
      || contextValue?.dependenceStructure !== 'independent'
    ),
  )
  const contextBindingStale = Boolean(
    analysisContext?.contextHash
    && model.contextHash
    && model.contextHash !== analysisContext.contextHash,
  )

  const {
    freezeMutation,
    analysisMutation,
    cancelMutation,
    analysisJob,
    analysisResult,
    analysisRunning,
  } = useModelBuilderAnalysis({
    dataset,
    model,
    overrideReason,
    activeRunId,
    setActiveRunId,
  })
  const editingLocked = analysisRunning || !draftHydrated || freezeMutation.isPending

  useEffect(() => {
    if (!analysisContext?.contextHash) return
    restoreModel(resetModelRef.current(dataset.id))
    setCustomMode(false)
    setValidation(null)
    setBuilderError(null)
    setDraftHydrated(false)
    setDraftState('saving')
    if (previousContextModelId.current !== contextModelId) setActiveRunId(null)
    previousContextModelId.current = contextModelId
    freezeMutation.reset()
    analysisMutation.reset()
    cancelMutation.reset()
  }, [analysisContext?.contextHash, contextModelId, dataset.id, restoreModel, freezeMutation.reset, analysisMutation.reset, cancelMutation.reset])

  const { draftMutation } = useModelBuilderDrafting({
    dataset,
    analysisContext,
    contextModelId,
    latestModel,
    setModel: restoreModel,
    setValidation,
    setTemplate,
    setCustomMode,
    setDraftState,
    setBuilderError,
    setDraftHydrated,
  })

  const handleUndo = useCallback(() => {
    if (editingLocked) return
    const prev = undo()
    if (prev) {
      freezeMutation.reset()
      analysisMutation.reset()
      cancelMutation.reset()
      setValidation(null)
      setActiveRunId(null)
      setModel(prev)
      setCustomMode(prev.name === '自定义 PROCESS 结构')
      const previousTemplate = (Object.keys(templateLabels) as ModelTemplate[]).find(key => templateLabels[key] === prev.name)
      if (previousTemplate) setTemplate(previousTemplate)
    }
  }, [undo, editingLocked, freezeMutation.reset, analysisMutation.reset, cancelMutation.reset])

  const handleRedo = useCallback(() => {
    if (editingLocked) return
    const next = redo()
    if (next) {
      freezeMutation.reset()
      analysisMutation.reset()
      cancelMutation.reset()
      setValidation(null)
      setActiveRunId(null)
      setModel(next)
      setCustomMode(next.name === '自定义 PROCESS 结构')
      const nextTemplate = (Object.keys(templateLabels) as ModelTemplate[]).find(key => templateLabels[key] === next.name)
      if (nextTemplate) setTemplate(nextTemplate)
    }
  }, [redo, editingLocked, freezeMutation.reset, analysisMutation.reset, cancelMutation.reset])

  useModelBuilderKeyboardShortcuts(handleUndo, handleRedo, setZenMode)

  useModelBuilderDraftPersistence({
    draftMutation,
    draftHydrated,
    model,
    draftState,
    setDraftState,
  })

  const {
    updateModel,
    switchEstimationFamily,
    applyTemplate,
    startCustomModel,
    assignVariable,
    addStructuralNode,
    removeStructuralNode,
    handleResetLayout,
  } = createModelBuilderActions({
    currentModel: model,
    editingLocked,
    bindNewModelContext,
    pushState,
    variables,
    measurement,
    setModel,
    setValidation,
    setActiveRunId,
    setTemplate,
    setCustomMode,
    setBuilderError,
    freezeMutation,
    analysisMutation,
    cancelMutation,
  })

  const {
    addCovariate,
    addVariableToCanvas,
    addEdge,
    removeCanvasNode,
    changeNodeRole,
    handleConnect,
    reconnectEdge,
  } = createModelCanvasHandlers(variables, model, updateModel, assignVariable, setBuilderError)

  const unusedVariables = variables.filter(
    (variable) => !model.nodes.some((node) => node.variableId === variable.id),
  )
  const recognitionLabel = validation?.displayName ?? (customMode ? '自定义 PROCESS 结构' : templateLabels[template])

  const pathEvidence = useMemo(
    () => buildPathEvidence(model, analysisResult, analysisRunning),
    [analysisResult, analysisRunning, model],
  )

  return {
    variables,
    indicatorCandidates,
    template,
    customMode,
    model,
    validation,
    draftState,
    builderError,
    overrideReason,
    setOverrideReason,
    zenMode,
    leftCollapsed,
    rightCollapsed,
    activeRunId,
    analysisJob,
    analysisResult,
    analysisRunning,
    editingLocked,
    freezeMutation,
    analysisMutation,
    cancelMutation,
    canUndo,
    canRedo,
    updateModel,
    handleUndo,
    handleRedo,
    applyTemplate,
    startCustomModel,
    assignVariable,
    addStructuralNode,
    removeStructuralNode,
    addCovariate,
    addVariableToCanvas,
    addEdge,
    removeCanvasNode,
    changeNodeRole,
    handleConnect,
    reconnectEdge,
    handleResetLayout,
    setZenMode,
    setLeftCollapsed,
    setRightCollapsed,
    pathEvidence,
    recognitionLabel,
    contextGateBlocked,
    contextBindingStale,
    unusedVariables,
    switchEstimationFamily,
  }
}
