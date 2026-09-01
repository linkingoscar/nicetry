import { useState } from 'react'
import type { ModelSpec, ModelVariable, NodeRole } from '../../types'
import { roleLabels } from './modelTemplates'

interface ModelVariableLibraryProps {
  variables: ModelVariable[]
  model: ModelSpec
  onAssignVariable: (nodeId: string, variableId: string) => void
  onAddCovariate: (variableId: string) => void
  onPlaceVariable: (variableId: string, position: { x: number; y: number }, targetNodeId?: string, role?: NodeRole) => void
  disabled?: boolean
}

export function ModelVariableLibrary({ variables, model, onAssignVariable, onAddCovariate, onPlaceVariable, disabled = false }: ModelVariableLibraryProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [target, setTarget] = useState('node_x')
  const [message, setMessage] = useState('')
  const structuralNodes = model.nodes.filter(node => node.role !== 'covariate')
  const targetId = target === '__covariate' || target.startsWith('__new_') || structuralNodes.some(node => node.id === target) ? target : structuralNodes[0]?.id ?? '__new_x'
  const selected = variables.find(variable => variable.id === selectedId)
  const owner = model.nodes.find(node => node.variableId === selectedId)
  const invalidSelection = !selected || !targetId || (targetId === '__covariate' ? Boolean(owner) : selected.dataType === 'nominal')
  const q = searchQuery.trim().toLocaleLowerCase()
  const filtered = variables.filter(variable => `${variable.label} ${variable.source} ${variable.dataType}`.toLocaleLowerCase().includes(q))
  const assign = () => {
    if (!selected || invalidSelection) return
    if (targetId === '__covariate') onAddCovariate(selected.id)
    else if (targetId.startsWith('__new_')) onPlaceVariable(selected.id, { x: 120 + (model.nodes.length % 4) * 210, y: 100 + Math.floor(model.nodes.length / 4) * 160 }, undefined, targetId.slice(6) as NodeRole)
    else onAssignVariable(targetId, selected.id)
    if (targetId.startsWith('__new_')) { setMessage('已提交新节点设置；如变量已绑定，请按画布提示调整。'); return }
    setMessage(`已分配“${selected.label}”到${targetId === '__covariate' ? '控制变量' : structuralNodes.find(node => node.id === targetId)?.role.toUpperCase()}。`)
  }
  return (
    <aside className="variable-library" aria-labelledby="variable-library-heading">
      <h2 id="variable-library-heading">变量库</h2>
      <p className="muted">点选变量，再分配角色；也可以拖到角色槽或画布。</p>
      <label className="process-variable-search">搜索变量<input type="search" value={searchQuery} onChange={event => setSearchQuery(event.target.value)} placeholder="名称或类型" /></label>
      <fieldset className="process-variable-assignment" disabled={disabled}>
        <legend>点按分配</legend>
        <p>{selected ? `已选：${selected.label}` : '先在下方选择一个变量'}</p>
        <label>目标角色<select value={targetId} onChange={event => setTarget(event.target.value)}>
          {structuralNodes.map(node => <option key={node.id} value={node.id}>{node.role.toUpperCase()} · {node.label}</option>)}
          <option value="__covariate">添加为控制变量</option>
          {(['x', 'm', 'y', 'w', 'z'] as const).map(role => <option key={role} value={`__new_${role}`}>新增 / 填入 {roleLabels[role]}</option>)}
        </select></label>
        <button type="button" className="secondary-button" disabled={invalidSelection} onClick={assign}>分配到所选角色</button>
        {selected?.dataType === 'nominal' && targetId !== '__covariate' ? <small>名义变量请放入控制变量区，并确认编码。</small> : null}
        {owner ? <small>当前绑定 {owner.role.toUpperCase()}；改分配会移动或交换绑定。</small> : null}
      </fieldset>
      <p className="process-assignment-status" role="status">{message}</p>
      {filtered.length === 0 ? <p className="muted">没有匹配的变量，请修改搜索词。</p> : null}
      {(['scale_score', 'observed'] as const).map(kind => {
        const group = filtered.filter(variable => variable.kind === kind)
        if (!group.length) return null
        return <div className="variable-group" key={kind}>
          <strong>{kind === 'scale_score' ? '构念得分' : '原始变量'}</strong>
          {group.map(variable => <button type="button" className="variable-token" key={variable.id} draggable={!disabled} disabled={disabled}
            aria-pressed={selectedId === variable.id} aria-label={`选择变量 ${variable.label}`}
            onClick={() => { setSelectedId(variable.id); setMessage('') }}
            onDragStart={event => event.dataTransfer.setData('text/researchpath-variable', variable.id)}>
            <span>{variable.label}</span><small>{variable.source}</small><em>{variable.encodingHint.label}</em>
          </button>)}
        </div>
      })}
    </aside>
  )
}
