import type { ModelSpec, ModelVariable, NodeRole } from '../../types'
import { roleLabels } from './modelTemplates'

interface RoleEditorSectionProps {
  model: ModelSpec
  variables: ModelVariable[]
  onAssignVariable: (nodeId: string, variableId: string) => void
  onAddStructuralNode: (role: Extract<NodeRole, 'm' | 'w' | 'z'>) => void
  onRemoveStructuralNode: (nodeId: string) => void
  onChangeNodeRole: (nodeId: string, role: NodeRole) => void
  onRenameNode: (nodeId: string, label: string) => void
}

export function RoleEditorSection({
  model,
  variables,
  onAssignVariable,
  onAddStructuralNode,
  onRemoveStructuralNode,
  onChangeNodeRole,
  onRenameNode,
}: RoleEditorSectionProps) {
  const structuralNodes = model.nodes

  return (
    <section className="role-editor" aria-labelledby="role-editor-heading">
      <div className="section-heading process-structure-heading">
        <div>
          <p className="eyebrow">PROCESS 5.0 结构</p>
          <h2 id="role-editor-heading">节点角色</h2>
        </div>
        {model.estimation.family === 'ols' ? (
          <fieldset className="structure-node-actions">
            <legend>添加结构节点</legend>
            <button type="button" className="text-button" onClick={() => onAddStructuralNode('m')}>添加 M</button>
            <button type="button" className="text-button" onClick={() => onAddStructuralNode('w')}>添加 W</button>
            <button type="button" className="text-button" onClick={() => onAddStructuralNode('z')}>添加 Z</button>
          </fieldset>
        ) : null}
      </div>
      <div className="role-slot-grid">
        {structuralNodes.map((node, nodeIndex) => (
          <fieldset
            className={`role-slot role-slot-${node.role}`}
            key={node.id}
            aria-label={`${roleLabels[node.role]}变量槽位`}
            onDragOver={(event) => {
              if (event.dataTransfer.types.includes('text/researchpath-variable')) event.preventDefault()
            }}
            onDrop={(event) => {
              const variableId = event.dataTransfer.getData('text/researchpath-variable')
              if (!variableId) return
              event.preventDefault()
              onAssignVariable(node.id, variableId)
            }}
          >
            <label>
              <span>
                {node.role === 'm'
                  ? `M${structuralNodes.slice(0, nodeIndex + 1).filter((candidate) => candidate.role === 'm').length} · 中介`
                  : roleLabels[node.role]}
              </span>
              <select value={node.variableId ?? ''} onChange={(event) => onAssignVariable(node.id, event.target.value)}>
                <option value="" disabled>-- 选择或拖入变量 --</option>
                {variables.filter((variable) => variable.dataType !== 'nominal').map((variable) => (
                  <option key={variable.id} value={variable.id}>{variable.label} · {variable.source}</option>
                ))}
              </select>
            </label>
            <label>角色<select aria-label={`变量属性 ${node.label}`} value={node.role} onChange={e => onChangeNodeRole(node.id, e.target.value as NodeRole)}>{Object.entries(roleLabels).map(([role, label]) => <option key={role} value={role}>{label}</option>)}</select></label>
            <label>显示名称<input aria-label={`节点显示名称 ${node.id}`} value={node.label} maxLength={120} onChange={e => onRenameNode(node.id, e.target.value)} /></label>
            {(
              <button
                type="button"
                className="text-button role-slot-remove"
                aria-label={`移除 ${node.role.toUpperCase()} 节点`}
                onClick={() => onRemoveStructuralNode(node.id)}
              >
                移除
              </button>
            )}
          </fieldset>
        ))}
      </div>
    </section>
  )
}
