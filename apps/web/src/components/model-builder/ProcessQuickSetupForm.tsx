import { useState } from 'react'

import type { ModelSpec, ModelVariable } from '../../types'
import type { ProcessQuickKind, ProcessQuickSetup } from './processQuickForm'

interface ProcessQuickSetupFormProps {
  variables: ModelVariable[]
  model: ModelSpec
  initialKind?: ProcessQuickKind
  disabled?: boolean
  onApply: (setup: ProcessQuickSetup) => boolean
  onOpenAdvanced: () => void
}

function currentVariable(model: ModelSpec, role: 'x' | 'm' | 'w' | 'y'): string {
  return model.nodes.find((node) => node.role === role)?.variableId ?? ''
}

function VariableRoleSelect({
  label,
  value,
  variables,
  disabled,
  onChange,
}: {
  label: string
  value: string
  variables: ModelVariable[]
  disabled?: boolean
  onChange: (value: string) => void
}) {
  return (
    <label>
      {label}
      <select value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
        <option value="">请选择变量</option>
        {variables.map((variable) => (
          <option key={variable.id} value={variable.id}>
            {variable.label} · {variable.dataType}
          </option>
        ))}
      </select>
    </label>
  )
}

export function ProcessQuickSetupForm({
  variables,
  model,
  initialKind = 'mediation',
  disabled = false,
  onApply,
  onOpenAdvanced,
}: ProcessQuickSetupFormProps) {
  const [kind, setKind] = useState<ProcessQuickKind>(initialKind)
  const [xVariableId, setXVariableId] = useState(() => currentVariable(model, 'x'))
  const [yVariableId, setYVariableId] = useState(() => currentVariable(model, 'y'))
  const [mediatorVariableId, setMediatorVariableId] = useState(() => currentVariable(model, 'm'))
  const [moderatorVariableId, setModeratorVariableId] = useState(() => currentVariable(model, 'w'))
  const [confidenceLevel, setConfidenceLevel] = useState(model.estimation.confidenceLevel || 0.95)
  const [bootstrapReplicates, setBootstrapReplicates] = useState(model.estimation.bootstrap.replicates || 5000)
  const [meanCenterPredictors, setMeanCenterPredictors] = useState(
    model.estimation.centering.method === 'mean',
  )

  const roleIds = kind === 'mediation'
    ? [xVariableId, mediatorVariableId, yVariableId]
    : [xVariableId, moderatorVariableId, yVariableId]
  const complete = roleIds.every(Boolean)
  const distinct = new Set(roleIds.filter(Boolean)).size === roleIds.filter(Boolean).length
  const bootstrapValid = Number.isInteger(bootstrapReplicates)
    && bootstrapReplicates >= 1000
    && bootstrapReplicates <= 50000
  const canApply = !disabled && complete && distinct && bootstrapValid

  const apply = () => {
    if (!canApply) return
    onApply({
      kind,
      xVariableId,
      yVariableId,
      mediatorVariableId: kind === 'mediation' ? mediatorVariableId : undefined,
      moderatorVariableId: kind === 'moderation' ? moderatorVariableId : undefined,
      confidenceLevel,
      bootstrapReplicates,
      meanCenterPredictors: kind === 'moderation' && meanCenterPredictors,
    })
  }

  return (
    <section className="context-method-runner" aria-labelledby="process-quick-form-heading">
      <header>
        <p className="eyebrow">常用 PROCESS 表单</p>
        <h2 id="process-quick-form-heading">中介 / 调节快速配置</h2>
        <p className="muted">先用表单声明最常见的变量角色和推断设置。应用后可直接在同页完成校验、冻结和运行；高级画布仅在需要自定义路径时打开。</p>
      </header>

      <fieldset className="process-editing-fields" disabled={disabled}>
        <legend>模型类型</legend>
        <div className="analysis-inline-actions">
          <button type="button" aria-pressed={kind === 'mediation'} onClick={() => setKind('mediation')}>
            简单中介 · Model 4
          </button>
          <button type="button" aria-pressed={kind === 'moderation'} onClick={() => setKind('moderation')}>
            简单调节 · Model 1
          </button>
        </div>

        <div className="method-catalog-filters">
          <VariableRoleSelect label="自变量 X" value={xVariableId} variables={variables} onChange={setXVariableId} />
          <VariableRoleSelect label="结果变量 Y" value={yVariableId} variables={variables} onChange={setYVariableId} />
          {kind === 'mediation' ? (
            <VariableRoleSelect label="中介变量 M" value={mediatorVariableId} variables={variables} onChange={setMediatorVariableId} />
          ) : (
            <VariableRoleSelect label="调节变量 W" value={moderatorVariableId} variables={variables} onChange={setModeratorVariableId} />
          )}
          <label>
            置信水平
            <select value={String(confidenceLevel)} onChange={(event) => setConfidenceLevel(Number(event.target.value))}>
              <option value="0.9">90%</option>
              <option value="0.95">95%</option>
              <option value="0.99">99%</option>
            </select>
          </label>
          <label>
            Bootstrap 次数
            <input
              type="number"
              min={1000}
              max={50000}
              step={1000}
              value={bootstrapReplicates}
              onChange={(event) => setBootstrapReplicates(Number(event.target.value))}
            />
          </label>
        </div>

        {kind === 'moderation' ? (
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={meanCenterPredictors}
              onChange={(event) => setMeanCenterPredictors(event.target.checked)}
            />
            对 X 与 W 做均值中心化
          </label>
        ) : null}
      </fieldset>

      {!distinct ? <p className="error-message" role="alert">X、Y 与中介/调节变量必须使用不同变量。</p> : null}
      {!bootstrapValid ? <p className="error-message" role="alert">Bootstrap 次数需为 1,000–50,000 之间的整数。</p> : null}
      <p className="method-note">应用表单只更新当前可撤销草稿，不会自动运行，也不会覆盖任何既有运行结果。</p>

      <div className="analysis-inline-actions">
        <button type="button" className="run-button" disabled={!canApply} onClick={apply}>应用表单设置</button>
        <button type="button" className="secondary-button" onClick={onOpenAdvanced}>打开高级编辑器</button>
      </div>
    </section>
  )
}
