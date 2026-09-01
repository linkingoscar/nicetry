import type { ModelSpec, ModelVariable, NodeRole } from '../../types'
import { nodeFromVariable, roleLabels } from './modelTemplates'
import { assignVariableToModel, removeModelEdges } from './modelStructureActions'

export function addVariableToCanvasModel(current: ModelSpec, variable: ModelVariable, position: { x: number; y: number }, role: NodeRole): ModelSpec {
  const existing = current.nodes.find(node => node.role === role)
  if (existing && ['x', 'y', 'w', 'z'].includes(role)) {
    if (existing.variableId) throw new Error(`${roleLabels[role]} 已有变量；请拖到该节点替换，或先修改已有节点的角色。`)
    const assigned = assignVariableToModel(current, existing.id, variable, [variable])
    return { ...assigned, canvas: { positions: { ...assigned.canvas?.positions, [existing.id]: position } } }
  }
  if (role === 'm' && current.nodes.filter(n => n.role === 'm').length >= 10) throw new Error('PROCESS 最多支持 10 个并行中介。')
  let sequence = 1
  let nodeId = `node_${role}`
  while (current.nodes.some(node => node.id === nodeId)) nodeId = `node_${role}${sequence++}`
  return {
    ...current,
    nodes: [...current.nodes, { ...nodeFromVariable(role, variable), id: nodeId }],
    // Placing a variable never invents regression paths or covariate assignments.
    canvas: { positions: { ...current.canvas?.positions, [nodeId]: position } },
  }
}

export function changeModelNodeRole(current: ModelSpec, nodeId: string, role: NodeRole): ModelSpec {
  const target = current.nodes.find(n => n.id === nodeId)
  if (!target || target.role === role) return current
  const occupied = ['x', 'y', 'w', 'z'].includes(role) ? current.nodes.find(n => n.role === role) : undefined
  const nodes = current.nodes.map(node => {
    const nextRole = node.id === nodeId ? role : node.id === occupied?.id ? target.role : node.role
    return { ...node, role: nextRole, label: node.variableId ? node.label : `拖入 ${roleLabels[nextRole]} 变量` }
  })
  const roles = new Map(nodes.map(n => [n.id, n.role]))
  const removed = current.estimation.family === 'ols' ? current.edges.filter(edge => !['x', 'm'].includes(roles.get(edge.from) ?? '') || !['m', 'y'].includes(roles.get(edge.to) ?? '')).map(edge => edge.id) : []
  const cleaned = removeModelEdges(current, removed)
  return {
    ...cleaned, nodes,
    moderations: cleaned.moderations.filter(mod => ['w', 'z'].includes(roles.get(mod.moderatorNodeId) ?? '') && (!mod.secondaryModeratorNodeId || ['w', 'z'].includes(roles.get(mod.secondaryModeratorNodeId) ?? ''))),
    covariates: cleaned.covariates.filter(c => roles.get(c.nodeId) === 'covariate').map(c => ({ ...c, outcomeNodeIds: c.outcomeNodeIds.filter(id => ['m', 'y'].includes(roles.get(id) ?? '')) })).filter(c => c.outcomeNodeIds.length > 0),
  }
}

export function reconnectModelEdge(current: ModelSpec, id: string, from: string, to: string): ModelSpec {
  if (from === to) throw new Error('路径的起点与终点不能相同。')
  if (current.edges.some(e => e.id !== id && e.from === from && e.to === to)) throw new Error('该方向的路径已经存在。')
  if (![from, to].every(nodeId => current.nodes.some(n => n.id === nodeId))) throw new Error('请选择当前画布中的节点。')
  return { ...current, edges: current.edges.map(e => e.id === id ? { ...e, from, to, label: '' } : e) }
}
