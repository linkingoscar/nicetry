import { lazy, Suspense, useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import {
  createStudyPlan,
  freezeStudyPlan,
  mapStudyPlanDataset,
  updateStudyPlan,
} from '../api/workflows'
import type { StudyContext } from '../types/study-context'
import type { DatasetVariable } from '../types/datasets'
import type { StudyPlanVersion } from '../types/workflows'
import {
  EMPTY_DRAFT,
  fromPlan,
  nextDraftItemId,
  PLANNING_FAMILIES,
  PRIMARY_ANALYSIS_OPTIONS,
  toPayload,
  type PlanDraft,
  type PlannedRoleDraft,
} from './planDraftUtils'
import { StudyContextSwitcher } from './shared/StudyContextSwitcher'

const AdvancedAnalysisManager = lazy(() => import('./advanced/AdvancedAnalysisManager').then(module => ({
  default: module.AdvancedAnalysisManager,
})))

interface PlanningWorkspaceProps {
  context: StudyContext
  onContextChange: (context: StudyContext) => void
  projectId?: string
  datasetId?: string | null
  datasetVariables?: Array<Pick<DatasetVariable, 'id' | 'label' | 'confirmedType' | 'inferredType'>>
}

export function PlanningWorkspace({
  context,
  onContextChange,
  projectId = 'default',
  datasetId = null,
  datasetVariables = [],
}: PlanningWorkspaceProps) {
  const [plan, setPlan] = useState<StudyPlanVersion | null>(null)
  const [draft, setDraft] = useState<PlanDraft>(EMPTY_DRAFT)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [deviationReason, setDeviationReason] = useState('')
  const [mappingResult, setMappingResult] = useState<{ status: string; mappingHash: string } | null>(null)
  const saveMutation = useMutation({
    mutationFn: () => plan
      ? updateStudyPlan(plan.id, plan.revision, toPayload(draft, context, projectId))
      : createStudyPlan(projectId, toPayload(draft, context, projectId)),
    onSuccess: (created) => {
      setPlan(created)
      setDraft(fromPlan(created))
      setMapping({})
      setDeviationReason('')
      setMappingResult(null)
    },
  })
  const freezeMutation = useMutation({
    mutationFn: () => freezeStudyPlan(plan?.id ?? ''),
    onSuccess: setPlan,
  })
  const mapMutation = useMutation({
    mutationFn: () => {
      const payload: Record<string, unknown> = { ...mapping }
      if (deviationReason.trim()) payload.deviationReason = deviationReason.trim()
      return mapStudyPlanDataset(
        plan?.id ?? '',
        datasetId ?? '',
        payload,
        deviationReason.trim() ? 'deviated' : 'ready',
      )
    },
    onSuccess: (result) => setMappingResult({ status: result.status, mappingHash: result.mappingHash }),
  })
  const plannedRoles: Array<Record<string, unknown>> = plan
    ? (plan.sampleDefinition.roles ?? []).map(role => role as Record<string, unknown>)
    : ((toPayload(draft, context, projectId).sampleDefinition as { roles?: Array<Record<string, unknown>> }).roles ?? [])
  const primaryFamily = draft.sliceId.split('.', 1)[0]
  const planError = saveMutation.error ?? freezeMutation.error ?? mapMutation.error
  const variablesForAdvanced = useMemo(() => datasetVariables.map(variable => ({
    id: variable.id,
    name: variable.label,
    label: variable.label,
    type: variable.confirmedType === 'continuous' ? 'numeric' as const : 'categorical' as const,
  })), [datasetVariables])

  const setRole = (index: number, key: keyof PlannedRoleDraft, value: string) => {
    setDraft(current => ({
      ...current,
      plannedRoles: current.plannedRoles.map((role, roleIndex) => roleIndex === index ? { ...role, [key]: key === 'level' ? Number(value) : value } : role),
    }))
  }

  return (
    <main className="planning-workspace">
      <header className="planning-hero">
        <div>
          <p className="eyebrow">规划新研究</p>
          <h1>把研究问题、估计对象和分析边界保存成可审计计划</h1>
          <p>计划阶段可以没有真实数据，但不能用固定问题或默认回归规格代替研究者的设计决策。冻结前会再次检查方法是否适用于当前研究上下文。</p>
        </div>
        <span className="status-chip">{datasetId ? '可映射真实数据' : '先规划，后映射数据'}</span>
      </header>
      <StudyContextSwitcher value={context} hasDataset={Boolean(datasetId)} onChange={onContextChange} />
      <section className="planning-stage-list" aria-label="规划步骤">
        <div className="is-current"><span>1</span><strong>研究问题与估计目标</strong><small>明确要回答的问题，以及要估计的效应或参数</small></div>
        <div className="is-current"><span>2</span><strong>变量、构念与识别结构</strong><small>声明结果、预测、处理、协变量、测量项和角色层级</small></div>
        <div className="is-current"><span>3</span><strong>主分析、稳健性与功效</strong><small>选择已登记的方法，并保存可复核的参数和敏感性路线</small></div>
      </section>

      <section className="planning-plan-card" aria-labelledby="planning-plan-heading">
        <div>
          <p className="eyebrow">StudyPlan 版本对象</p>
          <h2 id="planning-plan-heading">编辑研究设计计划</h2>
          <p className="muted">每次保存都会产生新的 draft revision；冻结后当前版本不可覆盖。</p>
        </div>
        <div className="planning-form-grid">
          <label>计划标题<input value={draft.title} onChange={event => setDraft(current => ({ ...current, title: event.target.value }))} disabled={plan?.status === 'frozen'} placeholder="例如：员工自主性对绩效的影响" /></label>
          <label>研究问题<textarea value={draft.researchQuestion} onChange={event => setDraft(current => ({ ...current, researchQuestion: event.target.value }))} disabled={plan?.status === 'frozen'} placeholder="例如：在控制任职年限后，自主性是否提高绩效？" /></label>
          <label>主假设<textarea value={draft.hypothesis} onChange={event => setDraft(current => ({ ...current, hypothesis: event.target.value }))} disabled={plan?.status === 'frozen'} placeholder="例如：自主性提高会带来更高的绩效。" /></label>
          <label>Estimand / 估计对象<input value={draft.estimand} onChange={event => setDraft(current => ({ ...current, estimand: event.target.value }))} disabled={plan?.status === 'frozen'} placeholder="例如：调整后的平均处理效应或 R² 增量" /></label>
          <label>缺失数据策略<textarea value={draft.missingDataStrategy} onChange={event => setDraft(current => ({ ...current, missingDataStrategy: event.target.value }))} disabled={plan?.status === 'frozen'} /></label>
        </div>

        <div className="planning-design-section">
          <h3>主分析方法</h3>
          <label>选择已登记 slice
            <select value={draft.sliceId} onChange={event => setDraft(current => ({ ...current, sliceId: event.target.value }))} disabled={plan?.status === 'frozen'}>
              {PRIMARY_ANALYSIS_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
            </select>
          </label>
          {primaryFamily === 'power_analysis' ? (
            <div className="planning-power-grid">
              <label>效应量<input type="number" min="0.001" step="0.01" value={draft.effectSize} onChange={event => setDraft(current => ({ ...current, effectSize: Number(event.target.value) }))} disabled={plan?.status === 'frozen'} /></label>
              <label>显著性水平<input type="number" min="0.001" max="0.49" step="0.01" value={draft.alpha} onChange={event => setDraft(current => ({ ...current, alpha: Number(event.target.value) }))} disabled={plan?.status === 'frozen'} /></label>
              <label>目标功效<input type="number" min="0.51" max="0.99" step="0.01" value={draft.targetPower} onChange={event => setDraft(current => ({ ...current, targetPower: Number(event.target.value) }))} disabled={plan?.status === 'frozen'} /></label>
              <label>预测变量数<input type="number" min="1" step="1" value={draft.predictors} onChange={event => setDraft(current => ({ ...current, predictors: Number(event.target.value) }))} disabled={plan?.status === 'frozen'} /></label>
              <label>组数<input type="number" min="1" step="1" value={draft.groups} onChange={event => setDraft(current => ({ ...current, groups: Number(event.target.value) }))} disabled={plan?.status === 'frozen'} /></label>
              <label>求解目标<select value={draft.solveFor} onChange={event => setDraft(current => ({ ...current, solveFor: event.target.value as PlanDraft['solveFor'] }))} disabled={plan?.status === 'frozen'}><option value="sample_size">所需样本量</option><option value="power">给定样本量下的功效</option><option value="effect_size">可检测效应量</option></select></label>
            </div>
          ) : <p className="method-note">该主分析不在规划页生成固定的模拟结果；冻结时会检查它是否已登记、可执行且符合当前上下文。</p>}
        </div>

        <div className="planning-design-section">
          <div className="planning-section-heading"><h3>计划变量角色</h3><button type="button" className="secondary-button" disabled={plan?.status === 'frozen'} onClick={() => setDraft(current => ({ ...current, plannedRoles: [...current.plannedRoles, { uiId: nextDraftItemId('role'), key: '', label: '', role: 'covariate', level: 1, acceptedTypes: '', structureRole: '' }] }))}>添加角色</button></div>
          {draft.plannedRoles.map((role, index) => (
            <div className="planning-role-row" key={role.uiId}>
              <input aria-label={`角色 ${index + 1} key`} value={role.key} placeholder="key，如 outcome" onChange={event => setRole(index, 'key', event.target.value)} disabled={plan?.status === 'frozen'} />
              <input aria-label={`角色 ${index + 1} label`} value={role.label} placeholder="显示名称" onChange={event => setRole(index, 'label', event.target.value)} disabled={plan?.status === 'frozen'} />
              <input aria-label={`角色 ${index + 1} role`} value={role.role} placeholder="语义角色" onChange={event => setRole(index, 'role', event.target.value)} disabled={plan?.status === 'frozen'} />
              <input aria-label={`角色 ${index + 1} accepted types`} value={role.acceptedTypes} placeholder="允许类型，如 continuous" onChange={event => setRole(index, 'acceptedTypes', event.target.value)} disabled={plan?.status === 'frozen'} />
              <select aria-label={`角色 ${index + 1} structure role`} value={role.structureRole} onChange={event => setRole(index, 'structureRole', event.target.value)} disabled={plan?.status === 'frozen'}><option value="">不绑定结构角色</option><option value="subjectId">subjectId</option><option value="clusterId">clusterId</option><option value="timeId">timeId</option><option value="groupId">groupId</option><option value="treatmentId">treatmentId</option></select>
              <button type="button" className="secondary-button" aria-label={`删除角色 ${index + 1}`} disabled={plan?.status === 'frozen' || draft.plannedRoles.length <= 1} onClick={() => setDraft(current => ({ ...current, plannedRoles: current.plannedRoles.filter((_, roleIndex) => roleIndex !== index) }))}>删除</button>
            </div>
          ))}
        </div>

        <div className="planning-design-section">
          <div className="planning-section-heading"><h3>构念与测量项</h3><button type="button" className="secondary-button" disabled={plan?.status === 'frozen'} onClick={() => setDraft(current => ({ ...current, constructs: [...current.constructs, { uiId: nextDraftItemId('construct'), id: '', label: '', itemIds: '' }] }))}>添加构念</button></div>
          {draft.constructs.length === 0 ? <p className="method-note">尚未声明构念；如果主分析使用已计分构念，可在这里记录构念 ID 与题项来源。</p> : null}
          {draft.constructs.map((construct, index) => (
            <div className="planning-construct-row" key={construct.uiId}>
              <input aria-label={`构念 ${index + 1} id`} value={construct.id} placeholder="构念 ID" onChange={event => setDraft(current => ({ ...current, constructs: current.constructs.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.target.value } : item) }))} disabled={plan?.status === 'frozen'} />
              <input aria-label={`构念 ${index + 1} label`} value={construct.label} placeholder="构念名称" onChange={event => setDraft(current => ({ ...current, constructs: current.constructs.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item) }))} disabled={plan?.status === 'frozen'} />
              <input aria-label={`构念 ${index + 1} item ids`} value={construct.itemIds} placeholder="题项 ID，以逗号分隔" onChange={event => setDraft(current => ({ ...current, constructs: current.constructs.map((item, itemIndex) => itemIndex === index ? { ...item, itemIds: event.target.value } : item) }))} disabled={plan?.status === 'frozen'} />
              <button type="button" className="secondary-button" disabled={plan?.status === 'frozen'} onClick={() => setDraft(current => ({ ...current, constructs: current.constructs.filter((_, itemIndex) => itemIndex !== index) }))}>删除</button>
            </div>
          ))}
        </div>

        <div className="planning-design-section">
          <div className="planning-section-heading"><h3>稳健性 / 敏感性分析路线</h3><button type="button" className="secondary-button" disabled={plan?.status === 'frozen'} onClick={() => setDraft(current => ({ ...current, robustnessAnalyses: [...current.robustnessAnalyses, { uiId: nextDraftItemId('robustness'), sliceId: '', rationale: '' }] }))}>添加路线</button></div>
          {draft.robustnessAnalyses.map((analysis, index) => (
            <div className="planning-construct-row" key={analysis.uiId}>
              <input aria-label={`稳健性分析 ${index + 1} slice`} value={analysis.sliceId} placeholder="登记的 sliceId" onChange={event => setDraft(current => ({ ...current, robustnessAnalyses: current.robustnessAnalyses.map((item, itemIndex) => itemIndex === index ? { ...item, sliceId: event.target.value } : item) }))} disabled={plan?.status === 'frozen'} />
              <input aria-label={`稳健性分析 ${index + 1} rationale`} value={analysis.rationale} placeholder="为什么需要这条敏感性路线" onChange={event => setDraft(current => ({ ...current, robustnessAnalyses: current.robustnessAnalyses.map((item, itemIndex) => itemIndex === index ? { ...item, rationale: event.target.value } : item) }))} disabled={plan?.status === 'frozen'} />
              <button type="button" className="secondary-button" disabled={plan?.status === 'frozen'} onClick={() => setDraft(current => ({ ...current, robustnessAnalyses: current.robustnessAnalyses.filter((_, itemIndex) => itemIndex !== index) }))}>删除</button>
            </div>
          ))}
        </div>

        <div className="planning-plan-status" role="status">
          {plan ? <><strong>{plan.status === 'frozen' ? '计划已冻结' : `草稿 revision ${plan.revision}`}</strong><code>{plan.planHash}</code></> : <strong>尚未保存计划草稿</strong>}
          {plan?.status === 'draft' ? <button type="button" className="secondary-button" onClick={() => freezeMutation.mutate()} disabled={freezeMutation.isPending}>{freezeMutation.isPending ? '冻结中…' : '冻结当前 revision'}</button> : null}
          {plan?.status !== 'frozen' ? <button type="button" className="run-button" onClick={() => saveMutation.mutate()} disabled={saveMutation.isPending || !draft.title.trim() || !draft.researchQuestion.trim() || !draft.estimand.trim()}>{saveMutation.isPending ? '保存中…' : plan ? '保存为新 revision' : '保存研究计划草稿'}</button> : null}
        </div>
        {planError ? <p className="error-message" role="alert">计划操作失败：{planError.message}</p> : null}
      </section>

      {plan?.status === 'frozen' && datasetId ? (
        <section className="planning-mapping-card" aria-labelledby="planning-mapping-heading">
          <div>
            <p className="eyebrow">StudyPlan → DatasetVersion</p>
            <h2 id="planning-mapping-heading">映射计划角色到实际变量</h2>
            <p className="muted">服务端会同时检查项目归属、变量存在性、声明的类型和结构角色；偏离必须明确记录。</p>
          </div>
          {plannedRoles.length > 0 ? (
            <div className="planning-mapping-grid">
              {plannedRoles.map((role, index) => {
                const key = String(role.key ?? role.id ?? role.role ?? `role_${index}`)
                return (
                  <label key={key}>
                    <span>{String(role.label ?? role.role ?? key)}</span>
                    <select value={mapping[key] ?? ''} onChange={(event) => setMapping(current => ({ ...current, [key]: event.target.value }))}>
                      <option value="">请选择实际变量</option>
                      {datasetVariables.map((variable) => <option value={variable.id} key={variable.id}>{variable.label} · {variable.confirmedType ?? variable.inferredType}</option>)}
                    </select>
                  </label>
                )
              })}
            </div>
          ) : <p className="method-note">当前计划没有声明变量角色；这只能保存为不完整映射。</p>}
          <label className="planning-deviation-field"><span>偏离说明（填写后状态为 deviated，至少 10 个字符）</span><textarea value={deviationReason} onChange={(event) => setDeviationReason(event.target.value)} minLength={deviationReason ? 10 : undefined} placeholder="例如：原计划的结果变量在当前数据版本中改用已确认的构念分数。" /></label>
          <div className="planning-mapping-actions">
            <button type="button" className="secondary-button" onClick={() => mapMutation.mutate()} disabled={mapMutation.isPending || plannedRoles.some((role, index) => !mapping[String(role.key ?? role.id ?? role.role ?? `role_${index}`)])}>{mapMutation.isPending ? '映射中…' : deviationReason.trim() ? '保存偏离映射' : '保存当前数据映射'}</button>
            {mappingResult ? <span role="status">状态：{mappingResult.status} · <code>{mappingResult.mappingHash}</code></span> : null}
          </div>
        </section>
      ) : null}

      <section className="planning-capability-section">
        <p className="eyebrow">可执行规格参考</p>
        <h2>浏览已登记的统计能力</h2>
        <p className="muted">这里的能力卡用于理解支持边界；正式运行仍必须回到真实数据上下文并创建当前分析草稿。</p>
        <Suspense fallback={<p className="method-note" aria-live="polite">正在加载能力目录…</p>}>
          <AdvancedAnalysisManager
            variables={variablesForAdvanced}
            constructs={draft.constructs.map(construct => ({ id: construct.id, label: construct.label, itemIds: construct.itemIds.split(',').map(value => value.trim()).filter(Boolean) }))}
            allowedFamilies={PLANNING_FAMILIES}
            catalogTitle="已登记的方法能力"
            catalogDescription="规划页只展示能力边界；不会把规划参数或占位结果当作真实分析结论。"
          />
        </Suspense>
      </section>
    </main>
  )
}
