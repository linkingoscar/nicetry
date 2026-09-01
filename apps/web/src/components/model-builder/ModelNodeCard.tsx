import { memo, useState } from 'react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'

import type { NodeRole } from '../../types'
import type { EvidenceStatus } from './pathEvidence'

export interface ModelNodeData extends Record<string, unknown> {
  nodeId: string
  role: string
  label: string
  detail: string
  status: EvidenceStatus
  latent: boolean
  unbound?: boolean
  level?: 'first_order' | 'higher_order'
  subIndicatorsCount?: number
  covariates?: string[]
  isExpanded?: boolean
  onToggleExpand?: () => void
  onEditMeasurement?: (nodeId: string) => void
  onDeleteNode?: (nodeId: string) => void
  onChangeNodeRole?: (nodeId: string, newRole: NodeRole) => void
}

export type ModelFlowNode = Node<ModelNodeData, 'model-node'>

export const ModelNodeCard = memo(function ModelNodeCard({ data, selected }: NodeProps<ModelFlowNode>) {
  const isHigherOrder = data.level === 'higher_order'
  const isEmpty = data.unbound || !data.detail || data.label.startsWith('拖入')
  const [editing, setEditing] = useState(false)
  const handleContextMenu = (event: React.MouseEvent) => {
    if (!data.onDeleteNode && !data.onChangeNodeRole) return
    event.preventDefault()
    event.stopPropagation()
    setEditing(true)
  }

  const roleOptions: { role: NodeRole; label: string }[] = [
    { role: 'x', label: 'X · 自变量' },
    { role: 'm', label: 'M · 中介' },
    { role: 'y', label: 'Y · 结果' },
    { role: 'w', label: 'W · 调节' },
    { role: 'z', label: 'Z · 调节2' },
    { role: 'covariate', label: '控制变量' },
  ]

  return (
    <section
      className={`model-node-card model-node-card-${data.role} is-${data.status}${data.latent ? ' is-latent' : ''}${isHigherOrder ? ' is-higher-order' : ''}${selected ? ' is-selected' : ''}${isEmpty ? ' is-empty' : ''}`}
      onContextMenu={handleContextMenu}
      aria-label={`模型节点 ${data.role.toUpperCase()}`}
    >
      <Handle type="target" position={Position.Left} className="model-handle" />
      <div className="node-badge-row">
        <span className="model-node-role" title={`变量角色: ${data.role.toUpperCase()}`}>
          <span className="role-accessibility-symbol">
            {['x', 'm', 'y', 'w', 'z'].includes(data.role) ? `[${data.role.toUpperCase()}]` : data.role === 'covariate' ? '[Cov]' : '◇'}
          </span>{' '}
          {data.role.toUpperCase()}
        </span>
        {isHigherOrder && <span className="node-level-badge">高阶 SEM 因子</span>}
      </div>
      <strong>{data.label}</strong>
      {data.detail ? <small>{data.detail}</small> : <small className="empty-hint">拖入变量进行绑定</small>}
      {data.onEditMeasurement ? <button type="button" className="nodrag" onClick={() => data.onEditMeasurement?.(data.nodeId)} aria-label={`编辑 ${data.label} 测量关系`}>编辑测量</button> : null}
      {data.onToggleExpand ? <button type="button" className="nodrag" aria-expanded={data.isExpanded} onClick={data.onToggleExpand} aria-label={`${data.isExpanded ? '折叠' : '展开'} ${data.label} 指标`}>{data.isExpanded ? '折叠指标' : '展开指标'}</button> : null}
      {data.covariates && data.covariates.length > 0 ? (
        <span
          className="node-covariates-badge"
          title={`控制变量 (${data.covariates.length}): ${data.covariates.join(', ')}`}
        >
          控制变量（{data.covariates.length}）
        </span>
      ) : null}
      {data.subIndicatorsCount ? (
        <span className="node-sub-info">
          包含 {data.subIndicatorsCount} 个低阶指标
        </span>
      ) : null}
      {data.status === 'running' ? <span className="node-running-indicator" role="status" aria-label="正在估计" /> : null}
      <Handle type="source" position={Position.Right} className="model-handle" />

      {data.onDeleteNode || data.onChangeNodeRole ? <button type="button" className="nodrag node-edit-button" aria-label={`编辑节点 ${data.label}`} aria-expanded={editing} onClick={() => setEditing(value => !value)}>编辑节点</button> : null}
      {editing && (data.onChangeNodeRole || data.onDeleteNode) ? (
        <div className="node-properties nodrag nowheel">
          {data.onChangeNodeRole ? <label>变量角色<select aria-label={`节点角色 ${data.label}`} value={data.role} onChange={e => data.onChangeNodeRole?.(data.nodeId, e.target.value as NodeRole)}>
            {roleOptions.map(option => <option key={option.role} value={option.role}>{option.label}</option>)}
          </select></label> : null}
          {data.onDeleteNode ? <button type="button" className="text-button danger-text" onClick={() => data.onDeleteNode?.(data.nodeId)}>删除节点及相关连线</button> : null}
          <button type="button" className="text-button" onClick={() => setEditing(false)}>收起属性</button>
        </div>
      ) : null}
    </section>
  )
})
