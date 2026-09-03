import type { MeasurementVersion, ModelSpec, ModelVariable, NodeRole } from '../../types'
import { assignVariableToModel } from './modelStructureActions'
import { createModelTemplate, type ModelTemplate } from './modelTemplates'

export type ProcessQuickKind = 'mediation' | 'moderation'

export interface ProcessQuickSetup {
  kind: ProcessQuickKind
  xVariableId: string
  yVariableId: string
  mediatorVariableId?: string
  moderatorVariableId?: string
  confidenceLevel: number
  bootstrapReplicates: number
  meanCenterPredictors: boolean
}

export function processTemplateForQuickSetup(kind: ProcessQuickKind): ModelTemplate {
  return kind === 'mediation' ? 'model_4' : 'model_1'
}

function requiredRoleAssignments(setup: ProcessQuickSetup): Array<[Extract<NodeRole, 'x' | 'm' | 'w' | 'y'>, string]> {
  if (setup.kind === 'mediation') {
    return [
      ['x', setup.xVariableId],
      ['m', setup.mediatorVariableId ?? ''],
      ['y', setup.yVariableId],
    ]
  }
  return [
    ['x', setup.xVariableId],
    ['w', setup.moderatorVariableId ?? ''],
    ['y', setup.yVariableId],
  ]
}

export function buildProcessQuickModel(
  setup: ProcessQuickSetup,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  const assignments = requiredRoleAssignments(setup)
  if (assignments.some(([, variableId]) => !variableId)) throw new Error('请完成所有必填变量角色。')
  const distinctIds = new Set(assignments.map(([, variableId]) => variableId))
  if (distinctIds.size !== assignments.length) throw new Error('X、Y 与中介/调节变量必须使用不同变量。')
  if (!Number.isFinite(setup.confidenceLevel) || setup.confidenceLevel <= 0 || setup.confidenceLevel >= 1) {
    throw new Error('置信水平必须介于 0 和 1 之间。')
  }
  if (!Number.isInteger(setup.bootstrapReplicates) || setup.bootstrapReplicates < 1000 || setup.bootstrapReplicates > 50000) {
    throw new Error('Bootstrap 次数必须为 1,000–50,000 之间的整数。')
  }

  const template = processTemplateForQuickSetup(setup.kind)
  let model = createModelTemplate(template, variables, measurement)

  assignments.forEach(([role, variableId]) => {
    const variable = variables.find((candidate) => candidate.id === variableId)
    const node = model.nodes.find((candidate) => candidate.role === role)
    if (!variable) throw new Error(`变量 ${variableId} 已不在当前数据/量表版本中。`)
    if (!node) throw new Error(`当前 PROCESS 模板缺少 ${role.toUpperCase()} 角色。`)
    model = assignVariableToModel(model, node.id, variable, variables)
  })

  const centeringNodeIds = setup.kind === 'moderation' && setup.meanCenterPredictors
    ? model.nodes.filter((node) => node.role === 'x' || node.role === 'w').map((node) => node.id)
    : []

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
