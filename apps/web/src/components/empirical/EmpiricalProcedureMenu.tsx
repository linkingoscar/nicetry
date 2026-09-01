import { useState } from 'react'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'

export function EmpiricalProcedureMenu() {
  const { procedures, config, onSelectProcedure, isRunning, capabilitiesLoading, capabilitiesError } = useEmpiricalAnalysisContext()
  const [search, setSearch] = useState('')
  const matches = procedures.filter((p) => `${p.label} ${p.family} ${p.hint}`.toLowerCase().includes(search.toLowerCase()))
  const families = [...new Set(matches.map((p) => p.family))]
  return <nav className="procedure-menu" aria-label="选择分析方法">
    <h2>分析</h2>
    <label className="procedure-search">查找分析方法<input type="search" placeholder="如：相关、EFA、回归" value={search} onChange={(e) => setSearch(e.target.value)} /></label>
    {capabilitiesLoading ? <p role="status">正在读取可执行方法…</p> : null}
    {capabilitiesError ? <p role="alert">无法读取方法目录，请刷新页面重试。</p> : null}
    {families.map((family) => <div className="procedure-family" key={family}>
      <h3>{family}</h3>
      {matches.filter((p) => p.family === family).map((p) => <button type="button" key={p.id}
        aria-pressed={config.procedure === p.id} disabled={isRunning} onClick={() => onSelectProcedure(p.id)}>{p.label}</button>)}
    </div>)}
    {!matches.length && !capabilitiesLoading && !capabilitiesError ? <p className="muted">没有匹配的可执行方法。</p> : null}
    <p className="method-note">仅列出当前数据结构允许且可执行的方法。PROCESS、SEM、实验、MI、ESEM/IRT 等仍可从“方法目录”进入专用配置。</p>
  </nav>
}
