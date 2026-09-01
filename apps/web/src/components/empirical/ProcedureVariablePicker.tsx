import { useState } from 'react'
import type { Candidate } from './EmpiricalAnalysisContext'

export function ProcedureVariablePicker({ label, candidates, selected, onChange }: {
  label: string
  candidates: Candidate[]
  selected: string[]
  onChange: (ids: string[]) => void
}) {
  const [search, setSearch] = useState('')
  const visible = candidates.filter((v) => `${v.label} ${v.id}`.toLowerCase().includes(search.toLowerCase()))
  return <fieldset className="procedure-variable-picker">
    <legend>{label} <span>已选 {selected.length}</span></legend>
    <label className="procedure-search">查找{label}<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
    <div className="procedure-picker-actions">
      <button type="button" onClick={() => onChange([...new Set([...selected, ...visible.map((v) => v.id)])])}>选择当前列表</button>
      <button type="button" onClick={() => onChange([])}>清空选择</button>
    </div>
    <div className="procedure-variable-list">
      {visible.map((v) => <label key={v.id}>
        <input type="checkbox" checked={selected.includes(v.id)} onChange={() => onChange(selected.includes(v.id) ? selected.filter((id) => id !== v.id) : [...selected, v.id])} />
        <span>{v.label}</span>
      </label>)}
      {!visible.length ? <p className="muted">没有匹配的变量。</p> : null}
    </div>
  </fieldset>
}
