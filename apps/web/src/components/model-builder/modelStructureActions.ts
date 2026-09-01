import type { ModelSpec, ModelVariable, NodeRole } from '../../types'
import { createEmptyNode, nodeFromVariable } from './modelTemplates'
import { removeLatentDefinitions } from './semModelIntegrity'

export function assignVariableToModel(
  current: ModelSpec,
  nodeId: string,
  variable: ModelVariable,
  variables: ModelVariable[],
): ModelSpec {
  const target = current.nodes.find((node) => node.id === nodeId)
  if (!target) return current
  const existing = current.nodes.find((node) => node.variableId === variable.id)
  const previousTarget = variables.find((item) => item.id === target.variableId)
  current = removeLatentDefinitions(current, [target.id, ...(existing ? [existing.id] : [])])
  const centerable = variable.dataType === 'continuous' || variable.dataType === 'ordinal'
  const wasCentered = current.estimation.centering.nodeIds.includes(target.id)
  const centeredNodeIds = current.estimation.centering.nodeIds.filter((id) => id !== target.id)
  return {
    ...current,
    nodes: current.nodes.map((node) => {
      if (node.id === target.id) return { ...node, ...nodeFromVariable(target.role, variable), id: node.id }
      if (existing && node.id === existing.id) {
        return { ...node, ...(previousTarget ? nodeFromVariable(node.role, previousTarget) : createEmptyNode(node.role)), id: node.id }
      }
      return node
    }),
    estimation: {
      ...current.estimation,
      centering: {
        ...current.estimation.centering,
        nodeIds: centerable && wasCentered && current.estimation.centering.method === 'mean'
          ? [...centeredNodeIds, target.id]
          : centeredNodeIds,
      },
    },
  }
}

export function addStructuralNodeModel(
  current: ModelSpec,
  role: Extract<NodeRole, 'm' | 'w' | 'z'>,
  _variables?: ModelVariable[],
): ModelSpec {
  if (role !== 'm' && current.nodes.some((node) => node.role === role)) return current
  const roleCount = current.nodes.filter((node) => node.role === role).length
  if (role === 'm' && roleCount >= 10) return current
  const suffix = role === 'm' ? String(roleCount + 1) : ''
  let nodeId = `node_${role}${suffix}`
  let sequence = roleCount + 1
  while (current.nodes.some((node) => node.id === nodeId)) {
    sequence += 1
    nodeId = `node_${role}${sequence}`
  }
  return {
    ...current,
    nodes: [...current.nodes, { ...createEmptyNode(role, suffix), id: nodeId }],
    canvas: {
      positions: {
        ...current.canvas?.positions,
        [nodeId]: {
          x: role === 'm' ? 360 + roleCount * 80 : 260 + roleCount * 120,
          y: role === 'm' ? 180 + roleCount * 35 : 330,
        },
      },
    },
  }
}

export function removeStructuralNodeModel(current: ModelSpec, nodeId: string): ModelSpec {
  const node = current.nodes.find((candidate) => candidate.id === nodeId)
  if (!node && !current.latents?.some(latent => latent.id === nodeId)) return current
  current = removeLatentDefinitions(current, [nodeId])
  const removedEdgeIds = new Set(
    current.edges
      .filter((edge) => edge.from === nodeId || edge.to === nodeId)
      .map((edge) => edge.id),
  )
  const positions = { ...current.canvas?.positions }
  delete positions[nodeId]
  delete positions[`sem:${nodeId}`]
  return {
    ...current,
    nodes: current.nodes.filter((candidate) => candidate.id !== nodeId),
    edges: current.edges.filter((edge) => !removedEdgeIds.has(edge.id)),
    moderations: current.moderations.filter((moderation) =>
      moderation.moderatorNodeId !== nodeId
      && moderation.secondaryModeratorNodeId !== nodeId
      && !removedEdgeIds.has(moderation.targetEdgeId),
    ),
    covariates: current.covariates.filter((cov) => cov.nodeId !== nodeId)
      .map((cov) => ({ ...cov, outcomeNodeIds: cov.outcomeNodeIds.filter((id) => id !== nodeId) })).filter(cov => cov.outcomeNodeIds.length > 0),
    estimation: {
      ...current.estimation,
      centering: {
        ...current.estimation.centering,
        nodeIds: current.estimation.centering.nodeIds.filter((id) => id !== nodeId),
      },
    },
    canvas: { positions },
  }
}

export function removeModelEdges(current: ModelSpec, edgeIds: string[]): ModelSpec {
  const removed = new Set(edgeIds)
  return {
    ...current,
    edges: current.edges.filter(edge => !removed.has(edge.id)),
    moderations: current.moderations.filter(moderation => !removed.has(moderation.targetEdgeId) && !removed.has(`moderation:${moderation.id}`)),
  }
}
