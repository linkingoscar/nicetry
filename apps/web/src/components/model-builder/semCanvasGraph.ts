import { MarkerType } from '@xyflow/react'
import type { ModelSpec } from '../../types'
import type { ModelFlowNode } from './ModelNodeCard'
import type { PathEvidence } from './pathEvidence'
import type { StatisticalFlowEdge } from './StatisticalEdge'

export type SemView = 'structure' | 'measurement' | 'full'
export const loadingEdgeId = (latentId: string, indicatorId: string) => `loading:${latentId}:${indicatorId}`

export interface SemCanvasOptions {
  view: SemView
  collapsed: string[]
  labels: Record<string, string>
  onEdit?: (latentId: string) => void
  onToggle?: (latentId: string) => void
}

export function buildSemMeasurementGraph(model: ModelSpec, base: ModelFlowNode[], evidence: Record<string, PathEvidence>, options: SemCanvasOptions) {
  const latents = model.latents ?? []
  const latentIds = new Set(latents.map(latent => latent.id))
  const nodes = new Map(base.map(node => [node.id, node]))
  // Observed structural nodes must not share the indicator column's default positions.
  if (options.view !== 'structure') {
    base.filter(node => !latentIds.has(node.id)).forEach((node, index) => {
      nodes.set(node.id, { ...node, position: model.canvas?.positions?.[`sem:${node.id}`] ?? { x: 1000, y: index * 210 } })
    })
  }
  const measurementIds = new Set<string>()
  const edges: StatisticalFlowEdge[] = []
  let nextRow = 0
  const defaultPositions = new Map<string, { x: number; y: number }>()
  for (const latent of latents.filter(item => item.level !== 'higher_order')) {
    defaultPositions.set(latent.id, { x: 330, y: nextRow })
    nextRow += options.collapsed.includes(latent.id) ? 210 : Math.max(210, latent.indicators.length * 125 + 30)
  }
  const higherFactors = latents.filter(item => item.level === 'higher_order')
  higherFactors.forEach((latent, index) => {
    const children = latent.indicators.flatMap(id => { const position = defaultPositions.get(id); return position ? [position.y] : [] })
    defaultPositions.set(latent.id, { x: 20 - index * 220, y: children.length ? children.reduce((a, b) => a + b, 0) / children.length : 0 })
  })
  latents.forEach((latent) => {
    const original = nodes.get(latent.id)
    const higher = latent.level === 'higher_order'
    const position = model.canvas?.positions?.[`sem:${latent.id}`] ?? defaultPositions.get(latent.id) ?? { x: 330, y: 0 }
    nodes.set(latent.id, {
      ...original,
      id: latent.id, type: 'model-node',
      position: options.view === 'structure' && original ? original.position : position,
      data: {
        ...original?.data,
        nodeId: latent.id, role: original?.data.role ?? '因子', label: latent.name,
        detail: `${latent.indicators.length} 个${higher ? '低阶因子' : '题项指标'}`,
        latent: true, level: latent.level, unbound: !latent.indicators.length,
        status: original?.data.status ?? 'idle',
        onEditMeasurement: options.onEdit,
        isExpanded: !options.collapsed.includes(latent.id),
        onToggleExpand: options.view === 'structure' ? undefined : () => options.onToggle?.(latent.id),
      },
    })
    measurementIds.add(latent.id)
    if (options.view === 'structure' || options.collapsed.includes(latent.id)) return
    latent.indicators.forEach((indicator, itemIndex) => {
      const observedNode = model.nodes.find(node => node.id === indicator || node.variableId === indicator)
      const targetId = latentIds.has(indicator) ? indicator : observedNode?.id ?? `indicator:${indicator}`
      measurementIds.add(targetId)
      if (!latentIds.has(indicator) && !nodes.has(targetId)) {
        nodes.set(targetId, {
          id: targetId, type: 'model-node', connectable: false, deletable: false,
          position: model.canvas?.positions?.[`sem:${targetId}`] ?? { x: position.x + 320, y: position.y + itemIndex * 125 },
          data: { nodeId: targetId, role: '题项', label: options.labels[indicator] ?? indicator,
            detail: indicator, latent: false, status: 'idle', onEditMeasurement: options.onEdit ? () => options.onEdit?.(latent.id) : undefined },
        })
      }
      const id = loadingEdgeId(latent.id, indicator)
      edges.push({
        id, source: latent.id, target: targetId, type: 'statistical', deletable: false,
        data: { label: '载荷', measurement: true, evidence: evidence[id] ?? { status: 'idle' } },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#566579', width: 15, height: 15 },
      })
    })
  })
  return {
    nodes: [...nodes.values()].filter(node => options.view === 'structure'
      ? model.nodes.some(structural => structural.id === node.id)
      : options.view === 'measurement' ? measurementIds.has(node.id) : true),
    edges,
  }
}
