import type { ModelNode, ModelVariable, NodeRole, VariableEncoding } from '../../types'
import { roleLabels } from './modelTemplateTypes'

export function nodeFromVariable(role: NodeRole, variable: ModelVariable, suffix = ''): ModelNode {
  const { method, referenceLevel, levels } = variable.encodingHint
  return {
    id: `node_${role}${suffix}`,
    variableId: variable.id,
    label: variable.label,
    kind: variable.kind,
    role,
    dataType: variable.dataType,
    encoding: {
      method,
      ...(referenceLevel !== undefined ? { referenceLevel } : {}),
      ...(levels !== undefined ? { levels } : {}),
    } satisfies VariableEncoding,
  }
}

export function createEmptyNode(role: NodeRole, suffix = ''): ModelNode {
  return {
    id: `node_${role}${suffix}`,
    variableId: undefined,
    label: `拖入 ${roleLabels[role] ?? role.toUpperCase()} 变量`,
    kind: 'observed',
    role,
    dataType: 'continuous',
  }
}
