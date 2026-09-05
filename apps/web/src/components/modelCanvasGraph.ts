import { MarkerType, type Edge } from '@xyflow/react'
import type { ModelSpec } from '../types'
import type { ModelFlowNode } from './model-builder/ModelNodeCard'
import type { ModerationFlowEdge } from './model-builder/ModerationEdge'
import type { EvidenceStatus, PathEvidence } from './model-builder/pathEvidence'
import type { StatisticalFlowEdge } from './model-builder/StatisticalEdge'

export const fallbackPositions: Record<string, { x: number; y: number }> = {
  x: { x: 60, y: 150 },
  m: { x: 330, y: 70 },
  y: { x: 640, y: 150 },
  w: { x: 260, y: 315 },
  covariate: { x: 560, y: 330 },
}

export function nodeStatus(
  nodeId: string,
  model: ModelSpec,
  evidence: Record<string, PathEvidence>,
): EvidenceStatus {
  const attached = model.edges
    .filter((edge) => edge.from === nodeId || edge.to === nodeId)
    .map((edge) => evidence[edge.id])
    .filter(Boolean)
  if (attached.some((item) => item.status === 'running')) return 'running'
  if (attached.some((item) => item.status === 'inference_uncertain')) return 'inference_uncertain'
  if (attached.length && attached.every((item) => item.status === 'inference_signal')) return 'inference_signal'
  return 'idle'
}

export function markerColor(status: EvidenceStatus, moderation = false) {
  if (status === 'inference_signal') return '#2c6ecb'
  if (status === 'inference_uncertain') return '#8b6f20'
  if (status === 'running') return moderation ? '#d28b16' : '#2c6ecb'
  return moderation ? '#bd7a0b' : '#566579'
}

export function buildRenderedNodes(
  model: ModelSpec,
  pathEvidence: Record<string, PathEvidence>,
  controlEdgeMode: 'compact' | 'all' | 'hidden',
  outcomeCovariates: Map<string, string[]>,
  onDeleteNode: ((nodeId: string) => void) | undefined,
  onChangeNodeRole: ModelFlowNode['data']['onChangeNodeRole'],
): ModelFlowNode[] {
  return model.nodes.map((node, index) => ({
    id: node.id,
    type: 'model-node' as const,
    position: model.canvas?.positions?.[node.id] ?? {
      ...(fallbackPositions[node.role] ?? { x: 80, y: 80 + index * 90 }),
      y: (fallbackPositions[node.role]?.y ?? 80) + (node.role === 'covariate' ? index * 62 : 0),
    },
    data: {
      nodeId: node.id,
      role: node.role,
      label: node.label,
      detail: node.kind === 'latent'
        ? `${model.latents?.find(latent => latent.id === node.id)?.indicators.length ?? 0} 个测量题项`
        : node.variableId ? (node.encoding?.method?.replaceAll('_', ' ') ?? node.kind) : '',
      unbound: node.kind === 'latent'
        ? !model.latents?.some(latent => latent.id === node.id && latent.indicators.length > 0)
        : !node.variableId,
      status: nodeStatus(node.id, model, pathEvidence),
      latent: node.kind === 'latent',
      covariates: controlEdgeMode === 'compact' ? outcomeCovariates.get(node.id) : undefined,
      onDeleteNode,
      onChangeNodeRole,
    },
  }))
}

export function buildModelEdges(
  model: ModelSpec,
  pathEvidence: Record<string, PathEvidence>,
  analysisStatus: string,
  controlEdgeMode: 'compact' | 'all' | 'hidden',
): Array<StatisticalFlowEdge | ModerationFlowEdge | Edge> {
  const statistical: StatisticalFlowEdge[] = model.edges.map((edge) => {
    const evidence = pathEvidence[edge.id] ?? { status: analysisStatus === 'running' ? 'running' : 'idle' }
    const fromNode = model.nodes.find((node) => node.id === edge.from)
    const toNode = model.nodes.find((node) => node.id === edge.to)
    return {
      id: edge.id,
      source: edge.from,
      target: edge.to,
      type: 'statistical' as const,
      data: { label: edge.label || `${fromNode?.role.toUpperCase()}→${toNode?.role.toUpperCase()}`, evidence, measurement: false },
      markerEnd: { type: MarkerType.ArrowClosed, color: markerColor(evidence.status), width: 18, height: 18 },
    }
  })
  const controls: StatisticalFlowEdge[] = controlEdgeMode === 'all'
    ? model.covariates.flatMap((assignment) => assignment.outcomeNodeIds.map((outcomeId) => ({
        id: `control:${assignment.nodeId}:${outcomeId}`,
        source: assignment.nodeId,
        target: outcomeId,
        type: 'statistical' as const,
        selectable: false,
        deletable: false,
        data: { label: '控制', evidence: { status: analysisStatus === 'running' ? 'running' : 'idle' }, measurement: true },
        markerEnd: { type: MarkerType.ArrowClosed, color: markerColor(analysisStatus === 'running' ? 'running' : 'idle'), width: 15, height: 15 },
      })))
    : []
  const moderation: ModerationFlowEdge[] = model.moderations.flatMap((item) => {
    const target = model.edges.find((edge) => edge.id === item.targetEdgeId)
    if (!target) return []
    const targetSource = model.nodes.find((node) => node.id === target.from)
    const targetTarget = model.nodes.find((node) => node.id === target.to)
    const evidence = pathEvidence[`moderation:${item.id}`] ?? { status: analysisStatus === 'running' ? 'running' : 'idle' }
    return [{
      id: `moderation:${item.id}`,
      source: item.moderatorNodeId,
      target: target.to,
      type: 'moderation' as const,
      selectable: true,
      deletable: true,
      reconnectable: false,
      data: {
        targetSourceId: target.from,
        targetTargetId: target.to,
        targetLabel: `${targetSource?.role.toUpperCase()}→${targetTarget?.role.toUpperCase()}`,
        moderatorLabel: [item.moderatorNodeId, item.secondaryModeratorNodeId]
          .filter(Boolean).map(id => model.nodes.find(node => node.id === id)?.role.toUpperCase() ?? '调节变量').join(' × '),
        evidence,
      },
      markerEnd: { type: MarkerType.ArrowClosed, color: markerColor(evidence.status, true), width: 17, height: 17 },
    }]
  })
  return [...controls, ...statistical, ...moderation]
}
