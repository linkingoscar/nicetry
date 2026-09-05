import type { UseMutationResult } from '@tanstack/react-query'
import type { Connection } from '@xyflow/react'

import type {
  AnalysisJob,
  DatasetVersion,
  DatasetVariable,
  FrozenModelVersion,
  MeasurementVersion,
  ModelSpec,
  ModelValidation,
  ModelVariable,
  NodeRole,
  ResultBundle,
} from '../../types'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { PathEvidence } from './pathEvidence'
import type { ProcessQuickSetup } from './processQuickForm'
import type { SemQuickSetup } from './semQuickForm'
import type { ModelTemplate } from './modelTemplates'

export interface UseModelBuilderStateOptions {
  dataset: DatasetVersion
  measurement: MeasurementVersion
  analysisContext?: ResolvedAnalysisContext | null
}

export interface ModelBuilderState {
  variables: ModelVariable[]
  indicatorCandidates: DatasetVariable[]
  template: ModelTemplate
  customMode: boolean
  model: ModelSpec
  validation: ModelValidation | null
  draftState: 'saving' | 'saved' | 'error'
  builderError: string | null
  overrideReason: string
  setOverrideReason: (value: string) => void
  zenMode: boolean
  leftCollapsed: boolean
  rightCollapsed: boolean
  activeRunId: string | null
  analysisJob: AnalysisJob | null | undefined
  analysisResult: ResultBundle | undefined
  analysisRunning: boolean
  editingLocked: boolean
  freezeMutation: UseMutationResult<FrozenModelVersion, Error, void, unknown>
  analysisMutation: UseMutationResult<AnalysisJob, Error, number | undefined, unknown>
  cancelMutation: UseMutationResult<AnalysisJob, Error, void, unknown>
  canUndo: boolean
  canRedo: boolean
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void
  handleUndo: () => void
  handleRedo: () => void
  applyProcessQuickSetup: (setup: ProcessQuickSetup) => boolean
  applySemQuickSetup: (setup: SemQuickSetup) => boolean
  applyTemplate: (nextTemplate: ModelTemplate, mediatorCount?: number) => void
  startCustomModel: () => void
  assignVariable: (nodeId: string, variableId: string) => void
  addStructuralNode: (role: Extract<NodeRole, 'm' | 'w' | 'z'>) => void
  removeStructuralNode: (nodeId: string) => void
  addCovariate: (variableId: string) => void
  addVariableToCanvas: (variableId: string, position: { x: number; y: number }, targetNodeId?: string, role?: NodeRole) => void
  addEdge: (source: string, target: string) => void
  removeCanvasNode: (nodeId: string) => void
  changeNodeRole: (nodeId: string, newRole: NodeRole) => void
  reconnectEdge: (id: string, from: string, to: string) => void
  handleConnect: (connection: Connection) => void
  handleResetLayout: () => void
  setZenMode: (value: boolean | ((prev: boolean) => boolean)) => void
  setLeftCollapsed: (value: boolean | ((prev: boolean) => boolean)) => void
  setRightCollapsed: (value: boolean | ((prev: boolean) => boolean)) => void
  pathEvidence: Record<string, PathEvidence>
  recognitionLabel: string
  contextGateBlocked: boolean
  contextBindingStale: boolean
  unusedVariables: ModelVariable[]
  switchEstimationFamily: (family: 'ols' | 'sem') => void
}
