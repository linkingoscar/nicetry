import { useId, useState } from 'react'
import { processPresets } from './processPresets.generated'
import { presetDescription, presetGroup, processPresetGraph, type ProcessPreset } from './processPresetGraph'
import type { ModelTemplate } from './modelTemplates'

function PresetPreview({ preset, count }: { preset: ProcessPreset; count: number }) {
  const markerId = useId().replace(/:/g, '')
  const graph = processPresetGraph(preset, count)
  const width = Math.max(...graph.nodes.map(n => graph.positions[`node_${n.symbol}`].x)) + 180
  const height = Math.max(...graph.nodes.map(n => graph.positions[`node_${n.symbol}`].y)) + 100
  const point = (id: string) => ({ x: graph.positions[id].x + 60, y: graph.positions[id].y + 25 })
  return <svg className="preset-preview" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Model ${preset.number} 路径预览，${count} 个中介`}>
    <defs><marker id={markerId} markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 Z" fill="currentColor" /></marker></defs>
    {graph.edges.map(edge => {
      const from = point(edge.from), to = point(edge.to)
      const dx = to.x - from.x, dy = to.y - from.y, distance = Math.hypot(dx, dy) || 1
      return <line key={edge.id} x1={from.x + dx / distance * 42} y1={from.y + dy / distance * 28} x2={to.x - dx / distance * 48} y2={to.y - dy / distance * 30} stroke="currentColor" strokeWidth="2" markerEnd={`url(#${markerId})`} />
    })}
    {graph.moderations.flatMap(mod => {
      const edge = graph.edges.find(e => e.id === mod.targetEdgeId)
      if (!edge) return null
      const a = point(edge.from), b = point(edge.to)
      return [mod.moderatorNodeId, ...(mod.secondaryModeratorNodeId ? [mod.secondaryModeratorNodeId] : [])].map(id => {
        const from = point(id)
        return <line key={`${mod.id}_${id}`} className="preset-moderation" x1={from.x} y1={from.y + 24} x2={(a.x + b.x) / 2} y2={(a.y + b.y) / 2} strokeWidth="2" strokeDasharray="7 5" markerEnd={`url(#${markerId})`} />
      })
    })}
    {graph.nodes.map(node => { const p = point(`node_${node.symbol}`); return <g key={node.symbol}>
      <rect x={p.x - 42} y={p.y - 24} width="84" height="48" rx="10" />
      <text x={p.x} y={p.y + 7} textAnchor="middle">{node.symbol.toUpperCase()}</text>
    </g> })}
  </svg>
}

export function ProcessPresetPicker({ onSelect, disabled }: { onSelect: (template: ModelTemplate, count?: number) => void; disabled: boolean }) {
  const [search, setSearch] = useState('')
  const [group, setGroup] = useState('全部')
  const [selected, setSelected] = useState<ProcessPreset>(processPresets[3])
  const [count, setCount] = useState<number>(selected.minM)
  const visible = processPresets.filter(p => (group === '全部' || presetGroup(p) === group) && `model ${p.number} ${presetGroup(p)} ${presetDescription(p)}`.toLowerCase().includes(search.trim().toLowerCase()))
  return <section className="process-preset-picker" aria-label="全部官方 PROCESS 预设">
    <div className="preset-search-row">
      <label>查找官方预设<input type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder="编号、调节阶段或模型类型" /></label>
      <label>模型类型<select value={group} onChange={e => setGroup(e.target.value)}>{['全部', ...new Set(processPresets.map(presetGroup))].map(g => <option key={g}>{g}</option>)}</select></label>
    </div>
    <p className="muted">PROCESS 5.0 的 55 个有效预设（编号范围 1–92，非连续）。选择编号预览，再应用到画布；W×Z 的具体调节项见下方说明与路径设置。</p>
    <div className="preset-browser">
      <fieldset className="preset-number-grid" aria-label="官方预设编号">
        {visible.map(p => <button key={p.number} type="button" aria-pressed={selected.number === p.number} onClick={() => { setSelected(p); setCount(p.minM) }} title={presetDescription(p)}>Model {p.number}</button>)}
        {!visible.length ? <p role="status">没有匹配的有效预设。试试其他编号或清空搜索。</p> : null}
      </fieldset>
      <div className="preset-detail">
        <strong>Model {selected.number} · {presetGroup(selected)}</strong>
        <PresetPreview preset={selected} count={count} />
        <p>{presetDescription(selected)}</p>
        <label>中介数量<select value={count} onChange={e => setCount(Number(e.target.value))} disabled={disabled || selected.minM === selected.maxM}>
          {Array.from({ length: selected.maxM - selected.minM + 1 }, (_, i) => selected.minM + i).map(n => <option key={n} value={n}>{n} 个</option>)}
        </select></label>
        <button type="button" className="secondary-button" disabled={disabled} onClick={() => onSelect(`model_${selected.number}`, count)}>应用 Model {selected.number} 到画布</button>
      </div>
    </div>
  </section>
}
