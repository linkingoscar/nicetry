import type { Dispatch, SetStateAction } from 'react'
import type { UseMutationResult } from '@tanstack/react-query'

import type {
  AnalysisJob,
  FrozenModelVersion,
  MeasurementVersion,
  ModelSpec,
  ModelValidation,
  ModelVariable,
  NodeRole,
} from '../../types'
import { addStructuralNodeModel, assignVariableToModel, removeStructuralNodeModel } from './modelStructureActions'
import { buildModelForEstimationFamily } from './modelBuilderEstimation'
import { createCustomModelTemplate, createModelTemplate, templateLabels, type ModelTemplate } from './modelTemplates'
import {
  buildProcessQuickModel,
  processTemplateForQuickSetup,
  type ProcessQuickSetup,
} from './processQuickForm'

interface ModelBuilderActionsDeps {
  currentModel: ModelSpec
  editingLocked?: boolean
  bindNewModelContext: (next: ModelSpec) => ModelSpec
  pushState: (next: ModelSpec) => void
  variables: ModelVariable[]
  measurement: MeasurementVersion
  setModel: Dispatch<SetStateAction<ModelSpec>>
  setValidation: (next: ModelValidation | null) => void
  setActiveRunId: (next: string | null) => void
  setTemplate: Dispatch<SetStateAction<ModelTemplate>>
  setCustomMode: Dispatch<SetStateAction<boolean>>
  setBuilderError: (next: string | null) => void
  freezeMutation: UseMutationResult<FrozenModelVersion, Error, void, unknown>
  analysisMutation: UseMutationResult<AnalysisJob, Error, number | undefined, unknown>
  cancelMutation: UseMutationResult<AnalysisJob, Error, void, unknown>
}

export function createModelBuilderActions({
  currentModel,
  editingLocked = false,
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
}: ModelBuilderActionsDeps) {
  const updateModel = (updater: (current: ModelSpec) => ModelSpec) => {
    if (editingLocked) return
    setValidation(null)
    freezeMutation.reset()
    analysisMutation.reset()
    cancelMutation.reset()
    setActiveRunId(null)
    setModel((current) => {
      const next = bindNewModelContext(updater(current))
      pushState(next)
      return next
    })
  }

  const switchEstimationFamily = (family: 'ols' | 'sem') => {
    if (currentModel.estimation.family === family) return
    updateModel((current) => buildModelForEstimationFamily(current, family, variables, measurement))
  }

  const applyProcessQuickSetup = (setup: ProcessQuickSetup): boolean => {
    if (editingLocked) return false
    try {
      const nextTemplate = processTemplateForQuickSetup(setup.kind)
      const nextModel = buildProcessQuickModel(setup, variables, measurement)
      setBuilderError(null)
      setCustomMode(false)
      setTemplate(nextTemplate)
      updateModel(() => nextModel)
      return true
    } catch (error) {
      setBuilderError(error instanceof Error ? error.message : 'PROCESS 快速表单配置失败')
      return false
    }
  }

  const applyTemplate = (nextTemplate: ModelTemplate, mediatorCount?: number) => {
    if (editingLocked) return
    if (!window.confirm(`确定要切换到“${templateLabels[nextTemplate]}”模板吗？这会覆盖您当前的画布编辑和自定义连线。`)) {
      return
    }
    try {
      setBuilderError(null)
      setCustomMode(false)
      setTemplate(nextTemplate)
      updateModel(() => createModelTemplate(nextTemplate, variables, measurement, mediatorCount))
    } catch (error) {
      setBuilderError(error instanceof Error ? error.message : '模板创建失败')
    }
  }

  const startCustomModel = () => {
    if (editingLocked) return
    if (!window.confirm('确定要开始自定义构建吗？当前画布将替换为空白的 X、Y 槽位；变量与路径由您指定，可撤销恢复。')) return
    try {
      setBuilderError(null)
      setCustomMode(true)
      updateModel(() => createCustomModelTemplate(variables, measurement))
    } catch (error) {
      setBuilderError(error instanceof Error ? error.message : '自定义结构创建失败')
    }
  }

  const assignVariable = (nodeId: string, variableId: string) => {
    const variable = variables.find((item) => item.id === variableId)
    if (!variable) return
    updateModel((current) => assignVariableToModel(current, nodeId, variable, variables))
  }

  const addStructuralNode = (role: Extract<NodeRole, 'm' | 'w' | 'z'>) => {
    updateModel((current) => addStructuralNodeModel(current, role, variables))
  }

  const removeStructuralNode = (nodeId: string) => {
    updateModel((current) => removeStructuralNodeModel(current, nodeId))
  }

  const handleResetLayout = () => {
    updateModel((current) => ({
      ...current,
      canvas: { positions: {} },
    }))
  }

  return {
    updateModel,
    switchEstimationFamily,
    applyProcessQuickSetup,
    applyTemplate,
    startCustomModel,
    assignVariable,
    addStructuralNode,
    removeStructuralNode,
    handleResetLayout,
  }
}
