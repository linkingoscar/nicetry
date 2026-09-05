import type { MeasurementVersion, ModelSpec, ModelVariable } from '../../types'
import { assignVariableToModel } from './modelStructureActions'
import { createModelTemplate, type ModelTemplate } from './modelTemplates'

export type ProcessQuickKind =
  | 'mediation'
  | 'parallel_mediation'
  | 'serial_mediation'
  | 'moderation'
  | 'moderated_mediation_first'
  | 'moderated_mediation_second'

export interface ProcessQuickSetup {
  kind: ProcessQuickKind
  xVariableId: string
  yVariableId: string
  mediatorVariableId?: string
  secondMediatorVariableId?: string
  moderatorVariableId?: string
  confidenceLevel: number
  bootstrapReplicates: number
  meanCenterPredictors: boolean
}

export const PROCESS_QUICK_KIND_LABELS: Record<ProcessQuickKind, string> = {
  mediation: '简单中介 · PROCESS Model 4',
  parallel_mediation: '并行中介 · PROCESS Model 4',
  serial_mediation: '链式中介 · PROCESS Model 6',
  moderation: '简单调节 · PROCESS Model 1',
  moderated_mediation_first: '第一阶段调节中介 · PROCESS Model 7',
  moderated_mediation_second: '第二阶段调节中介 · PROCESS Model 14',
}

export function processTemplateForQuickSetup(kind: ProcessQuickKind): ModelTemplate {
  if (kind === 'moderation') return 'model_1'
  if (kind === 'serial_mediation') return 'model_6'
  if (kind === 'moderated_mediation_first') return 'model_7'
  if (kind === 'moderated_mediation_second') return 'model_14'
  return 'model_4'
}

export function processQuickKindForRequest(
  processModelNumber?: 1 | 4 | 6 | 7 | 14,
  mediatorCount?: number,
): ProcessQuickKind | null {
  if (processModelNumber === 1) return 'moderation'
  if (processModelNumber === 6) return 'serial_mediation'
  if (processModelNumber === 7) return 'moderated_mediation_first'
  if (processModelNumber === 14) return 'moderated_mediation_second'
  if (processModelNumber === 4) return mediatorCount && mediatorCount > 1 ? 'parallel_mediation' : 'mediation'
  return null
}

export function processQuickUsesModerator(kind: ProcessQuickKind): boolean {
  return kind === 'moderation'
    || kind === 'moderated_mediation_first'
    || kind === 'moderated_mediation_second'
}

export function processQuickCenteringRoles(kind: ProcessQuickKind): Array<'x' | 'm' | 'w'> {
  if (!processQuickUsesModerator(kind)) return []
  return kind === 'moderated_mediation_second' ? ['m', 'w'] : ['x', 'w']
}

function processQuickMediatorCount(kind: ProcessQuickKind): number {
  if (kind === 'parallel_mediation' || kind === 'serial_mediation') return 2
  if (kind === 'mediation' || kind === 'moderated_mediation_first' || kind === 'moderated_mediation_second') return 1
  return 0
}

function assignedVariableIds(setup: ProcessQuickSetup): string[] {
  const ids = [setup.xVariableId, setup.yVariableId]
  const mediatorCount = processQuickMediatorCount(setup.kind)
  if (mediatorCount >= 1) ids.push(setup.mediatorVariableId ?? '')
  if (mediatorCount >= 2) ids.push(setup.secondMediatorVariableId ?? '')
  if (processQuickUsesModerator(setup.kind)) ids.push(setup.moderatorVariableId ?? '')
  return ids
}

export function buildProcessQuickModel(
  setup: ProcessQuickSetup,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  const variableIds = assignedVariableIds(setup)
  if (variableIds.some((variableId) => !variableId)) throw new Error('请完成所有必填变量角色。')
  if (new Set(variableIds).size !== variableIds.length) throw new Error('X、Y、中介与调节角色必须使用不同变量。')
  if (!Number.isFinite(setup.confidenceLevel) || setup.confidenceLevel <= 0 || setup.confidenceLevel >= 1) {
    throw new Error('置信水平必须介于 0 和 1 之间。')
  }
  if (!Number.isInteger(setup.bootstrapReplicates) || setup.bootstrapReplicates < 1000 || setup.bootstrapReplicates > 50000) {
    throw new Error('Bootstrap 次数必须为 1,000–50,000 之间的整数。')
  }

  const template = processTemplateForQuickSetup(setup.kind)
  const mediatorCount = processQuickMediatorCount(setup.kind)
  let model = createModelTemplate(
    template,
    variables,
    measurement,
    mediatorCount > 1 ? mediatorCount : undefined,
  )

  const xNode = model.nodes.find((node) => node.role === 'x')
  const yNode = model.nodes.find((node) => node.role === 'y')
  const mediatorNodes = model.nodes.filter((node) => node.role === 'm')
  const moderatorNode = model.nodes.find((node) => node.role === 'w')
  const assignments = [
    [xNode?.id, setup.xVariableId],
    [yNode?.id, setup.yVariableId],
    ...(mediatorCount >= 1 ? [[mediatorNodes[0]?.id, setup.mediatorVariableId ?? '']] : []),
    ...(mediatorCount >= 2 ? [[mediatorNodes[1]?.id, setup.secondMediatorVariableId ?? '']] : []),
    ...(processQuickUsesModerator(setup.kind) ? [[moderatorNode?.id, setup.moderatorVariableId ?? '']] : []),
  ] as Array<[string | undefined, string]>

  assignments.forEach(([nodeId, variableId]) => {
    const variable = variables.find((candidate) => candidate.id === variableId)
    if (!variable) throw new Error(`变量 ${variableId} 已不在当前数据/量表版本中。`)
    if (!nodeId) throw new Error('当前 PROCESS 模板缺少所需变量角色。')
    model = assignVariableToModel(model, nodeId, variable, variables)
  })

  const centeringRoles = setup.meanCenterPredictors ? processQuickCenteringRoles(setup.kind) : []
  const centeringNodeIds = model.nodes
    .filter((node) => centeringRoles.includes(node.role as 'x' | 'm' | 'w'))
    .map((node) => node.id)

  return {
    ...model,
    estimation: {
      ...model.estimation,
      confidenceLevel: setup.confidenceLevel,
      bootstrap: {
        ...model.estimation.bootstrap,
        enabled: true,
        replicates: setup.bootstrapReplicates,
      },
      centering: {
        method: centeringNodeIds.length ? 'mean' : 'none',
        nodeIds: centeringNodeIds,
      },
    },
  }
}
