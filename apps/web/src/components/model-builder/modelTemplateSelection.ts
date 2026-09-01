import type { ModelVariable, NodeRole } from '../../types'
import { roleLabels, templateLabels, type ModelTemplate } from './modelTemplateTypes'

export type StructuralRole = Exclude<NodeRole, 'covariate'>

export function templateRoles(template: ModelTemplate): StructuralRole[] {
  if (template === 'model_1') return ['x', 'y', 'w']
  if (template === 'model_2' || template === 'model_3') {
    return ['x', 'y', 'w', 'z']
  }
  if (template === 'model_21' || template === 'model_22') {
    return ['x', 'm', 'y', 'w', 'z']
  }
  if (template === 'model_4') return ['x', 'm', 'y']
  return ['x', 'm', 'y', 'w']
}

export function selectTemplateVariables(
  template: ModelTemplate,
  variables: ModelVariable[],
  roles: StructuralRole[],
): ModelVariable[] {
  const structuralVariables = variables.filter((variable) => variable.dataType !== 'nominal')
  const selected: ModelVariable[] = []
  const used = new Set<string>()

  for (const role of roles) {
    const candidates = role === 'm' || role === 'y'
      ? structuralVariables.filter((variable) => ['continuous', 'binary'].includes(variable.dataType))
      : structuralVariables
    const variable = candidates.find((candidate) => !used.has(candidate.id))
    if (!variable) {
      if (role === 'm' || role === 'y') {
        const required = roles.filter((item) => item === 'm' || item === 'y').length
        const available = structuralVariables.filter((candidate) => ['continuous', 'binary'].includes(candidate.dataType)).length
        throw new Error(`${templateLabels[template]} 需要至少 ${required} 个连续或二分类变量用于 M/Y；当前仅有 ${available} 个。`)
      }
      throw new Error(`${templateLabels[template]} 缺少可用于 ${roleLabels[role]} 的数值变量。`)
    }
    selected.push(variable)
    used.add(variable.id)
  }
  return selected
}
