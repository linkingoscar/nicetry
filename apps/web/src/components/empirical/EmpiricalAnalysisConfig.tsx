import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import { EmpiricalProcedureFields } from './EmpiricalProcedureFields'
import { procedureDefinition, procedureReadiness } from './empiricalProcedures'

export type { EmpiricalConfigValue } from './empiricalConfigTypes'

export function EmpiricalAnalysisConfig() {
  const { config, configExpanded: expanded, procedures, isRunning, analysisJob, cancelPending,
    error, onToggleExpanded, onRun, onCancel, runHistory, onSelectRun, activeRunId } = useEmpiricalAnalysisContext()
  const definition = procedureDefinition(config.procedure)
  const readiness = procedureReadiness(config)
  const available = procedures.some((p) => p.id === config.procedure)
  return <section className="empirical-config" aria-labelledby="empirical-config-heading">
    <div className="section-heading empirical-config-heading">
      <div><p className="eyebrow">选择方法 → 指定变量 → 运行</p><h2 id="empirical-config-heading">{definition.label}</h2></div>
      <button className="config-toggle" type="button" aria-expanded={expanded} aria-controls="empirical-config-body" onClick={onToggleExpanded}>{expanded ? '收起设置' : '修改设置'}</button>
    </div>
    <p className="method-note">{definition.hint}</p>
    <label className="procedure-history">运行记录（当前数据与测量版本）
      <select value={activeRunId ?? ''} disabled={isRunning} onChange={(e) => onSelectRun(e.target.value)}>
        <option value="">选择历史运行…</option>
        {runHistory.map((run) => <option key={run.id} value={run.id}>{procedureDefinition(run.procedure).label} · {new Date(run.createdAt).toLocaleString()} · {run.id.slice(-6)}</option>)}
      </select>
    </label>
    {expanded ? <div id="empirical-config-body" className="empirical-config-body">
      <fieldset className="procedure-form" disabled={isRunning}>
        <legend className="sr-only">{definition.label}设置</legend>
        <EmpiricalProcedureFields />
      </fieldset>
      <div className="analysis-run-panel">
        <div><strong>仅运行：{definition.label}</strong><span>{readiness ?? (available ? '变量已选择；提交后由引擎验证模型与样本条件。' : '此方法尚未获得当前能力目录的执行许可。')}</span></div>
        <button className="run-button" type="button" disabled={isRunning || !!readiness || !available} onClick={onRun}>{isRunning ? '正在运行所选分析…' : `运行${definition.label}`}</button>
      </div>
    </div> : null}
    {isRunning && analysisJob ? <div className="analysis-progress" aria-live="polite">
      <div><span>{analysisJob.stage}</span><span>{Math.round(analysisJob.progress * 100)}%</span></div>
      <button type="button" disabled={analysisJob.status === 'cancelling' || cancelPending} onClick={() => onCancel(analysisJob.id)}>{analysisJob.status === 'cancelling' ? '正在取消…' : '取消分析'}</button>
      <progress value={analysisJob.progress} max={1} />
    </div> : null}
    {error ? <p className="error-message error-banner" role="alert">{error}</p> : null}
  </section>
}
