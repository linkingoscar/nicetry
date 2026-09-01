import { useState } from 'react'
import type { ModelSpec } from '../../types'
import { removeModelEdges } from './modelStructureActions'

interface PathEditorSectionProps {
  model: ModelSpec
  onAddEdge: (source: string, target: string) => void
  onUpdateModel: (updater: (current: ModelSpec) => ModelSpec) => void
}

export function PathEditorSection({ model, onAddEdge, onUpdateModel }: PathEditorSectionProps) {
  const [newEdgeSource, setNewEdgeSource] = useState('node_x')
  const [newEdgeTarget, setNewEdgeTarget] = useState('node_y')
  const structuralNodes = model.nodes.filter((node) => node.role !== 'covariate')
  const pathSourceNodes = structuralNodes.filter((node) => node.role === 'x' || node.role === 'm')
  const pathTargetNodes = structuralNodes.filter((node) => node.role === 'm' || node.role === 'y')
  const sourceId = pathSourceNodes.some(node => node.id === newEdgeSource) ? newEdgeSource : pathSourceNodes[0]?.id ?? ''
  const targetId = pathTargetNodes.some(node => node.id === newEdgeTarget) ? newEdgeTarget : pathTargetNodes[0]?.id ?? ''
  const cannotAdd = !sourceId || !targetId || sourceId === targetId || model.edges.some(edge => edge.from === sourceId && edge.to === targetId)

  return (
    <section className="path-editor" aria-labelledby="path-editor-heading">
      <div className="section-heading dictionary-heading-row">
        <div><p className="eyebrow">Regression edges</p><h2 id="path-editor-heading">路径</h2></div>
        <div className="add-edge-controls">
          <select aria-label="新增路径起点" value={sourceId} onChange={(event) => setNewEdgeSource(event.target.value)}>
            {pathSourceNodes.map((node) => <option key={node.id} value={node.id}>{node.role.toUpperCase()} · {node.label}</option>)}
          </select>
          <span>→</span>
          <select aria-label="新增路径终点" value={targetId} onChange={(event) => setNewEdgeTarget(event.target.value)}>
            {pathTargetNodes.map((node) => <option key={node.id} value={node.id}>{node.role.toUpperCase()} · {node.label}</option>)}
          </select>
          <button type="button" className="secondary-button" disabled={cannotAdd} onClick={() => onAddEdge(sourceId, targetId)}>添加路径</button>
        </div>
      </div>
      <div className="path-list">
        {model.edges.map((edge) => {
          const sourceNode = model.nodes.find((node) => node.id === edge.from)
          const targetNode = model.nodes.find((node) => node.id === edge.to)
          return (
            <div className="path-row" key={edge.id}>
              <strong>{sourceNode?.role.toUpperCase() ?? edge.from} → {targetNode?.role.toUpperCase() ?? edge.to}</strong>
              <span>{sourceNode?.label}</span>
              <span>→ {targetNode?.label}</span>
              <button
                type="button"
                className="text-button"
                aria-label={`删除路径 ${sourceNode?.label ?? edge.from} → ${targetNode?.label ?? edge.to}`}
                onClick={() => onUpdateModel((current) => removeModelEdges(current, [edge.id]))}
              >删除</button>
            </div>
          )
        })}
      </div>
    </section>
  )
}
