import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Background,
  BackgroundVariant,
  ConnectionLineType,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  SelectionMode,
  useReactFlow,
  useNodesState,
  useEdgesState,
  type Connection,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import type { ModelSpec, NodeRole } from '../types'
import { CanvasDropRolePicker, CanvasEdgeEditor } from './model-builder/CanvasEditingControls'
import { ModelNodeCard, type ModelFlowNode } from './model-builder/ModelNodeCard'
import { ModerationEdge, type ModerationFlowEdge } from './model-builder/ModerationEdge'
import type { PathEvidence } from './model-builder/pathEvidence'
import { StatisticalEdge, type StatisticalFlowEdge } from './model-builder/StatisticalEdge'
import {
  buildModelEdges,
  buildRenderedNodes,
} from './modelCanvasGraph'
import { ZoomScaleBadge } from './ModelCanvasZoomBadge'
import { buildSemMeasurementGraph, type SemCanvasOptions } from './model-builder/semCanvasGraph'

interface ModelCanvasProps {
  model: ModelSpec
  semOptions?: SemCanvasOptions
  pathEvidence?: Record<string, PathEvidence>
  analysisStatus?: 'idle' | 'queued' | 'running' | 'cancelling' | 'succeeded' | 'failed' | 'cancelled'
  progress?: number
  statusLabel?: string
  editable?: boolean
  onPositionChange?: (nodeId: string, position: { x: number; y: number }) => void
  onConnect?: (connection: Connection) => void
  onDeleteEdges?: (edgeIds: string[]) => void
  onDeleteNode?: (nodeId: string) => void
  onChangeNodeRole?: (nodeId: string, newRole: import('../types').NodeRole) => void
  onDropVariable?: (variableId: string, position: { x: number; y: number }, targetNodeId?: string, role?: NodeRole) => void
  onReconnectEdge?: (id: string, from: string, to: string) => void
}

const nodeTypes = { 'model-node': ModelNodeCard }
const edgeTypes = { statistical: StatisticalEdge, moderation: ModerationEdge }

function ModelCanvasInner({
  model,
  semOptions,
  pathEvidence = {},
  analysisStatus = 'idle',
  progress = 0,
  statusLabel = '识别中',
  editable = false,
  onPositionChange,
  onConnect,
  onDeleteEdges,
  onDeleteNode,
  onChangeNodeRole,
  onDropVariable,
  onReconnectEdge,
}: ModelCanvasProps) {
  const [controlEdgeMode, setControlEdgeMode] = useState<'compact' | 'all' | 'hidden'>('compact')
  const [variableDragOver, setVariableDragOver] = useState(false)
  const [pendingDrop, setPendingDrop] = useState<{ variableId: string; position: { x: number; y: number } } | null>(null)
  const [dropRole, setDropRole] = useState<NodeRole | ''>('')
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const handleSelectionChange = useCallback(({ edges: selected }: { edges: Edge[] }) => setSelectedEdgeId(selected[0]?.id ?? null), [])
  const reactFlow = useReactFlow<ModelFlowNode>()

  const outcomeCovariates = useMemo(() => {
    const map = new Map<string, string[]>()
    for (const assignment of model.covariates) {
      const covNode = model.nodes.find((n) => n.id === assignment.nodeId)
      const label = covNode?.label ?? assignment.nodeId
      for (const outcomeId of assignment.outcomeNodeIds) {
        const list = map.get(outcomeId) ?? []
        list.push(label)
        map.set(outcomeId, list)
      }
    }
    return map
  }, [model.covariates, model.nodes])

  const renderedNodes = useMemo<ModelFlowNode[]>(
    () => {
      const base = buildRenderedNodes(model, pathEvidence, controlEdgeMode, outcomeCovariates, editable ? onDeleteNode : undefined, editable ? onChangeNodeRole : undefined)
      return semOptions ? buildSemMeasurementGraph(model, base, pathEvidence, semOptions).nodes : base
    },
    [controlEdgeMode, model, onChangeNodeRole, onDeleteNode, outcomeCovariates, pathEvidence, semOptions, editable],
  )
  const [nodes, setNodes, onNodesChange] = useNodesState<ModelFlowNode>(renderedNodes)
  const semView = semOptions?.view
  const visibleNodeCount = renderedNodes.length
  useEffect(() => {
    if (!semView || !visibleNodeCount) return
    const timer = window.setTimeout(() => { void reactFlow.fitView({ padding: 0.2, duration: 0 }) }, 80)
    return () => window.clearTimeout(timer)
  }, [semView, visibleNodeCount, reactFlow])

  useEffect(() => {
    // Keep measured dimensions and selection while updating the model data.
    // Dropping measurements can leave virtualized nodes outside the viewport
    // unable to mount again after an edit or panel resize.
    setNodes(current => renderedNodes.map(next => ({ ...current.find(node => node.id === next.id), ...next })))
  }, [renderedNodes, setNodes])

  const renderedEdges = useMemo<Array<StatisticalFlowEdge | ModerationFlowEdge | Edge>>(
    () => [...(semOptions?.view === 'measurement' ? [] : buildModelEdges(model, pathEvidence, analysisStatus, controlEdgeMode)),
      ...(semOptions ? buildSemMeasurementGraph(model, [], pathEvidence, semOptions).edges : [])],
    [analysisStatus, controlEdgeMode, model, pathEvidence, semOptions],
  )
  const [edges, setEdges, onEdgesChange] = useEdgesState(renderedEdges)
  useEffect(() => { setEdges(current => renderedEdges.map(next => ({ ...current.find(edge => edge.id === next.id), ...next }))) }, [renderedEdges, setEdges])

  const isRunning = ['queued', 'running', 'cancelling'].includes(analysisStatus)
  const [alignmentGuides, setAlignmentGuides] = useState<Array<{ type: 'horizontal' | 'vertical'; coord: number }>>([])

  const handleNodeDrag = (_: MouseEvent | TouchEvent, node: ModelFlowNode) => {
    const nodeW = node.measured?.width ?? 168
    const nodeH = node.measured?.height ?? 90
    const nodeCx = node.position.x + nodeW / 2
    const nodeCy = node.position.y + nodeH / 2

    const guides: Array<{ type: 'horizontal' | 'vertical'; coord: number }> = []
    const threshold = 8

    for (const other of nodes) {
      if (other.id === node.id) continue
      const otherW = other.measured?.width ?? 168
      const otherH = other.measured?.height ?? 90
      const otherCx = other.position.x + otherW / 2
      const otherCy = other.position.y + otherH / 2

      if (Math.abs(nodeCx - otherCx) < threshold) {
        guides.push({ type: 'vertical', coord: otherCx })
        node.position.x = otherCx - nodeW / 2
      }
      if (Math.abs(nodeCy - otherCy) < threshold) {
        guides.push({ type: 'horizontal', coord: otherCy })
        node.position.y = otherCy - nodeH / 2
      }
    }

    setAlignmentGuides(guides)
  }

  const handleNodeDragStop = (_: MouseEvent | TouchEvent, node: ModelFlowNode) => {
    setAlignmentGuides([])
    onPositionChange?.(node.id, node.position)
  }

  return (
    <section className={`canvas-panel${isRunning ? ' is-analysis-running' : ''}`} aria-labelledby="model-heading">
      <div className="section-heading canvas-heading">
        <div><p className="eyebrow">实时路径模型</p><h2 id="model-heading">{model.name}</h2></div>
        <div className="canvas-status">
          {model.covariates.length > 0 ? (
            <button
              type="button"
              className="secondary-button"
              style={{ padding: '3px 8px', fontSize: '11px', borderRadius: '6px' }}
              onClick={() => setControlEdgeMode((prev) => prev === 'compact' ? 'all' : prev === 'all' ? 'hidden' : 'compact')}
              title="切换控制变量连线模式"
            >
              控制连线：{controlEdgeMode === 'compact' ? '自适应徽章' : controlEdgeMode === 'all' ? '显示全部' : '隐藏'}
            </button>
          ) : null}
          <span className="status-chip">{statusLabel}</span>
          {isRunning ? <span className="analysis-live-dot">估计中 {Math.round(progress * 100)}%</span> : null}
        </div>
      </div>
      <aside className="path-legend" aria-label="路径状态图例">
        <span><i className="legend-line is-idle" />待估计</span>
        <span><i className="legend-line is-running" />计算中</span>
        <span><i className="legend-line is-inference-signal" />区间不含 0 / p&lt;.05（非理论支持）</span>
        <span><i className="legend-line is-inference-uncertain" />区间含 0 / p≥.05（非无效证据）</span>
        <span><i className="legend-line is-moderation" />调节指向路径</span>
      </aside>
      {editable ? <p className="canvas-edit-help">拖到空白处选择变量角色；拖到节点绑定变量。点击“编辑节点”切换角色或删除，点击连线修改方向或删除；也可拖动连线端点重新连接。未完成的模型可保存，检查通过后才能运行。</p> : null}
      {editable && pendingDrop ? <CanvasDropRolePicker role={dropRole} onRoleChange={setDropRole} onCancel={() => setPendingDrop(null)} onConfirm={() => {
        if (!dropRole) return
        onDropVariable?.(pendingDrop.variableId, pendingDrop.position, undefined, dropRole)
        setPendingDrop(null)
      }} /> : null}
      {editable && selectedEdgeId ? <CanvasEdgeEditor model={model} edgeId={selectedEdgeId} onReconnect={onReconnectEdge} onDelete={onDeleteEdges} onClose={() => setSelectedEdgeId(null)} /> : null}
      <section
        className={`canvas${variableDragOver ? ' is-variable-drop-target' : ''}`}
        aria-label="回归路径模型"
        onDragOver={(event) => {
          if (!editable) return
          if (!event.dataTransfer.types.includes('text/researchpath-variable')) return
          event.preventDefault()
          event.dataTransfer.dropEffect = 'copy'
          setVariableDragOver(true)
        }}
        onDragLeave={() => setVariableDragOver(false)}
        onDrop={(event) => {
          if (!editable) return
          const variableId = event.dataTransfer.getData('text/researchpath-variable')
          if (!variableId) return
          event.preventDefault()
          setVariableDragOver(false)
          const position = reactFlow.screenToFlowPosition({ x: event.clientX, y: event.clientY })
          const targetNode = reactFlow.getNodes().find((node) => {
            const width = node.measured?.width ?? 168
            const height = node.measured?.height ?? 90
            return position.x >= node.position.x
              && position.x <= node.position.x + width
              && position.y >= node.position.y
              && position.y <= node.position.y + height
          })
          if (targetNode) onDropVariable?.(variableId, position, targetNode.id)
          else { setDropRole(''); setPendingDrop({ variableId, position }) }
        }}
      >
        {variableDragOver ? <span className="canvas-drop-hint">松开以放置变量：落在节点上替换，落在空白处新增</span> : null}
        {alignmentGuides.map((guide) => (
          <div
            key={`${guide.type}-${guide.coord}`}
            className={`canvas-alignment-guide is-${guide.type}`}
            style={{
              [guide.type === 'vertical' ? 'left' : 'top']: guide.coord,
            }}
          />
        ))}
        <ReactFlow<ModelFlowNode, StatisticalFlowEdge | ModerationFlowEdge>
          nodes={nodes}
          edges={edges as Array<StatisticalFlowEdge | ModerationFlowEdge>}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          edgesReconnectable={editable}
          onReconnect={(edge, connection) => { if (editable && connection.source && connection.target) onReconnectEdge?.(edge.id, connection.source, connection.target) }}
          onEdgeClick={(_, edge) => { if (editable) setSelectedEdgeId(edge.id) }}
          onPaneClick={() => setSelectedEdgeId(null)}
          onSelectionChange={handleSelectionChange}
          fitView
          fitViewOptions={{ padding: 0.2, duration: 280 }}
          minZoom={0.12}
          maxZoom={1.8}
          nodesDraggable={editable}
          nodesConnectable={editable && (!semOptions || semOptions.view === 'structure')}
          elementsSelectable={editable}
          connectionLineType={ConnectionLineType.Straight}
          connectionLineStyle={{ stroke: '#2b3a6a', strokeWidth: 2 }}
          nodeDragThreshold={1}
          elevateNodesOnSelect
          onNodeDrag={handleNodeDrag}
          onNodeDragStop={handleNodeDragStop}
          onConnect={onConnect}
          onEdgesDelete={(deleted) => { if (editable) onDeleteEdges?.(deleted.filter((edge) => !edge.id.includes(':') || edge.id.startsWith('moderation:')).map((edge) => edge.id)) }}
          onNodesDelete={(deleted) => deleted.forEach(node => { onDeleteNode?.(node.id) })}
          selectionKeyCode="Shift"
          multiSelectionKeyCode={['Control', 'Meta']}
          selectionMode={SelectionMode.Partial}
          panOnDrag={[1, 2]}
          deleteKeyCode={editable ? ['Backspace', 'Delete'] : null}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1.25} color="#cbced7" />
          <Controls showInteractive={editable} position="bottom-right" />
          <ZoomScaleBadge />
        </ReactFlow>
      </section>
    </section>
  )
}

export function ModelCanvas(props: ModelCanvasProps) {
  return (
    <ReactFlowProvider>
      <ModelCanvasInner {...props} />
    </ReactFlowProvider>
  )
}
