import type { ModelSpec, NodeRole } from '../../types'
import { roleLabels } from './modelTemplates'

export function CanvasDropRolePicker({ role, onRoleChange, onConfirm, onCancel }: { role: NodeRole | ''; onRoleChange: (role: NodeRole | '') => void; onConfirm: () => void; onCancel: () => void }) {
  return <fieldset className="canvas-property-panel" aria-label="放置新变量">
    <legend>放置新变量</legend>
    <label>新变量角色<select value={role} onChange={e => onRoleChange(e.target.value as NodeRole | '')}>
      <option value="">请选择变量角色…</option>
      {(Object.entries(roleLabels) as Array<[NodeRole, string]>).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
    </select></label>
    <p>不会自动添加路径。X / Y / W / Z 各保留一个槽位；已有空槽时绑定该槽位。</p>
    <button type="button" className="secondary-button" disabled={!role} onClick={onConfirm}>确认放置变量</button>
    <button type="button" className="text-button" onClick={onCancel}>取消放置</button>
  </fieldset>
}

export function CanvasEdgeEditor({ model, edgeId, onReconnect, onDelete, onClose }: { model: ModelSpec; edgeId: string; onReconnect?: (id: string, from: string, to: string) => void; onDelete?: (ids: string[]) => void; onClose: () => void }) {
  const edge = model.edges.find(item => item.id === edgeId)
  const mod = model.moderations.find(item => `moderation:${item.id}` === edgeId)
  if (!edge && !mod) return null
  const nodes = model.nodes.filter(n => !['covariate', 'w', 'z'].includes(n.role))
  return <fieldset className="canvas-property-panel" aria-label="选中连线属性">
    <legend>{mod ? '调节连线' : '回归路径'}</legend>
    {edge ? <>
      <label>连线起点<select value={edge.from} onChange={e => onReconnect?.(edge.id, e.target.value, edge.to)}>{nodes.map(n => <option key={n.id} value={n.id}>{n.role.toUpperCase()} · {n.label}</option>)}</select></label>
      <span aria-hidden="true">→</span>
      <label>连线终点<select value={edge.to} onChange={e => onReconnect?.(edge.id, edge.from, e.target.value)}>{nodes.map(n => <option key={n.id} value={n.id}>{n.role.toUpperCase()} · {n.label}</option>)}</select></label>
      <button type="button" className="secondary-button" onClick={() => onReconnect?.(edge.id, edge.to, edge.from)}>反转箭头</button>
    </> : <p>该虚线表示调节某条回归路径；在“路径与调节”中可更换调节变量和目标路径。</p>}
    <button type="button" className="text-button danger-text" onClick={() => { onDelete?.([edgeId]); onClose() }}>删除连线</button>
    <button type="button" className="text-button" onClick={onClose}>收起连线属性</button>
  </fieldset>
}
