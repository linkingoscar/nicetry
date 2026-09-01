import type { ModelEdge, ModelNode, NodeRole } from '../../types'
import { roleLabels } from './modelTemplates'

interface RoleEditorSectionProps {
  structuralNodes: ModelNode[]
  onRoleChange: (nodeId: string, role: NodeRole) => void
  onRemoveNode: (nodeId: string) => void
}

export function RoleEditorSection({
  structuralNodes,
  onRoleChange,
  onRemoveNode,
}: RoleEditorSectionProps) {
  return (
    <section className="role-editor" aria-labelledby="role-editor-heading">
      <div className="section-heading process-structure-heading">
        <div>
          <p className="eyebrow">PROCESS 5.0 结构</p>
          <h2 id="role-editor-heading">节点角色</h2>
        </div>
      </div>
      <div className="role-slot-grid">
        {structuralNodes.map((node) => (
          <fieldset className={`role-slot role-slot-${node.role}`} key={node.id} aria-label={`${roleLabels[node.role]}变量槽位`}>
            <legend>{roleLabels[node.role]}</legend>
            <div className="role-slot-controls">
              <select
                aria-label={`${roleLabels[node.role]} 节点角色`}
                value={node.role}
                onChange={(e) => {
                  const role = e.target.value as NodeRole
                  onRoleChange(node.id, role)
                }}
              >
                <option value="x">自变量 (X)</option>
                <option value="y">因变量 (Y)</option>
                <option value="m">中介变量 (M)</option>
                <option value="w">调节变量 (W)</option>
                <option value="z">三阶调节 (Z)</option>
              </select>
              <button
                type="button"
                className="text-button"
                onClick={() => onRemoveNode(node.id)}
              >
                移除
              </button>
            </div>
          </fieldset>
        ))}
      </div>
    </section>
  )
}

interface PathEditorSectionProps {
  nodes: ModelNode[]
  edges: ModelEdge[]
  newEdgeSource: string
  newEdgeTarget: string
  onSourceChange: (value: string) => void
  onTargetChange: (value: string) => void
  onAddEdge: () => void
  onDeleteEdge: (edgeId: string) => void
}

export function PathEditorSection({
  nodes,
  edges,
  newEdgeSource,
  newEdgeTarget,
  onSourceChange,
  onTargetChange,
  onAddEdge,
  onDeleteEdge,
}: PathEditorSectionProps) {
  return (
    <section className="path-editor" aria-labelledby="path-editor-heading">
      <h2 id="path-editor-heading">路径与回归线</h2>
      <div className="path-add-form">
        <select aria-label="新增路径起点" value={newEdgeSource} onChange={(e) => onSourceChange(e.target.value)}>
          {nodes.map((n) => <option key={n.id} value={n.id}>{n.label} ({roleLabels[n.role]})</option>)}
        </select>
        <span>→</span>
        <select aria-label="新增路径终点" value={newEdgeTarget} onChange={(e) => onTargetChange(e.target.value)}>
          {nodes.map((n) => <option key={n.id} value={n.id}>{n.label} ({roleLabels[n.role]})</option>)}
        </select>
        <button type="button" className="secondary-button" onClick={onAddEdge}>添加路径</button>
      </div>
      <ul className="edge-list">
        {edges.map((edge) => (
          <li key={edge.id}>
            <span>{nodes.find((n) => n.id === edge.from)?.label} → {nodes.find((n) => n.id === edge.to)?.label}</span>
            <button
              type="button"
              className="text-button"
              onClick={() => onDeleteEdge(edge.id)}
            >
              删除
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
