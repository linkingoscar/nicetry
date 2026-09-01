import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import { ProcedureVariablePicker } from './ProcedureVariablePicker'
import { EmpiricalRegressionSection } from './empiricalConfigRegressionSection'
import { MeasurementModelSection } from './empiricalConfigSections'
import { EmpiricalAnalysisAdvancedSections } from './empiricalConfigAdvancedSections'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'

export function EmpiricalProcedureFields() {
  const { config: value, onConfigChange: onChange, measurement, analysisCandidates, allCandidates,
    groupCandidates, aggregationCandidates, sampleVersions } = useEmpiricalAnalysisContext()
  const p = value.procedure
  const variables = ['descriptives', 'correlation', 'groups', 'frequencies', 'missing'].includes(p)
  const scales = ['reliability', 'efa', 'cfa', 'validity', 'common_method', 'invariance', 'aggregation'].includes(p)
  return <>
    {variables ? <ProcedureVariablePicker label="分析变量" candidates={['frequencies', 'missing'].includes(p) ? allCandidates : analysisCandidates}
      selected={value.analysisVariableIds} onChange={(analysisVariableIds) => onChange({ analysisVariableIds,
        groupVariableId: p === 'groups' && analysisVariableIds.includes(value.groupVariableId ?? '') ? null : value.groupVariableId,
        controlVariableIds: value.controlVariableIds.filter((id) => !analysisVariableIds.includes(id)) })} /> : null}
    {scales ? <>
      <ProcedureVariablePicker label="量表与题项" candidates={(measurement?.constructs ?? []).map((c) => ({ id: c.id, label: `${c.name}（${c.itemIds.length} 题）` }))}
        selected={value.constructIds} onChange={(constructIds) => onChange({ constructIds })} />
      <p className="method-note">使用测量版本已确认的题项、反向计分与构念结构；只分析勾选的量表。</p>
    </> : null}
    <div className="empirical-config-grid">
      {p === 'groups' ? <p className="method-note">多重比较选项控制跨分析变量的总体检验（omnibus）校正；组内事后比较使用各检验方法报告的校正，不套用其他方法的默认值。</p> : null}
      {['groups', 'invariance'].includes(p) ? <label>分组变量<select value={value.groupVariableId ?? ''} onChange={(event) => onChange({ groupVariableId: event.target.value || null })}>
        <option value="">请选择</option>{groupCandidates.filter((v) => p === 'invariance' || !value.analysisVariableIds.includes(v.id)).map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
      </select></label> : null}
      {p === 'aggregation' ? <label>cluster 聚合变量<select value={value.aggregationVariableId ?? ''} onChange={(event) => onChange({ aggregationVariableId: event.target.value || null })}>
        <option value="">请选择</option>{aggregationCandidates.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
      </select></label> : null}
      {p === 'correlation' ? <label>相关分析方法<select value={value.correlationMethod} onChange={(event) => onChange({ correlationMethod: event.target.value as EmpiricalConfigValue['correlationMethod'] })}>
        <option value="pearson">Pearson 积差相关</option><option value="spearman">Spearman 秩相关</option><option value="partial">偏相关</option>
      </select></label> : null}
    </div>
    {p === 'correlation' && value.correlationMethod === 'partial' ? <ProcedureVariablePicker label="控制变量"
      candidates={analysisCandidates.filter((v) => !value.analysisVariableIds.includes(v.id))} selected={value.controlVariableIds}
      onChange={(controlVariableIds) => onChange({ controlVariableIds })} /> : null}
    {p === 'efa' ? <MeasurementModelSection /> : null}
    {['regression', 'relative_importance', 'response_surface'].includes(p) ? <EmpiricalRegressionSection /> : null}
    {['longitudinal', 'diary'].includes(p) ? <EmpiricalAnalysisAdvancedSections /> : null}
    <details className="analysis-config-section">
      <summary><strong>样本与统计选项</strong></summary>
      <div className="empirical-config-grid">
        <label>分析样本版本（可选）<select value={value.sampleVersionId ?? ''} onChange={(event) => onChange({ sampleVersionId: event.target.value || null })}>
          <option value="">使用当前数据全部案例</option>{sampleVersions?.map((sample) => <option key={sample.id} value={sample.id}>{sample.label} · 纳入 {sample.includedCount}</option>)}
        </select></label>
        <label>置信水平<select value={value.confidenceLevel} onChange={(event) => onChange({ confidenceLevel: Number(event.target.value) })}>
          <option value={0.9}>90%</option><option value={0.95}>95%</option><option value={0.99}>99%</option>
        </select></label>
        {['correlation', 'groups', 'regression'].includes(p) ? <label>多重比较校正<select value={p === 'groups' ? value.groupOmnibusPAdjust : p === 'correlation' ? value.correlationPAdjust : value.multiplicityPAdjust} onChange={(event) => {
          const method = event.target.value as EmpiricalConfigValue['multiplicityPAdjust']
          onChange({ multiplicityPAdjust: method, correlationPAdjust: method, groupOmnibusPAdjust: method })
        }}><option value="BH">BH / FDR</option><option value="holm">Holm / FWER</option><option value="none">不校正（需披露）</option></select></label> : null}
      </div>
    </details>
  </>
}
