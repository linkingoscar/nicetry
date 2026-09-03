import { useState } from 'react'

import type { MeasurementVersion, ModelSpec } from '../../types'
import type { SemQuickSetup } from './semQuickForm'

interface SemQuickSetupFormProps {
  measurement: MeasurementVersion
  model: ModelSpec
  disabled?: boolean
  onApply: (setup: SemQuickSetup) => boolean
  onOpenAdvanced: () => void
}

export function SemQuickSetupForm({
  measurement,
  model,
  disabled = false,
  onApply,
  onOpenAdvanced,
}: SemQuickSetupFormProps) {
  const constructs = measurement.constructs
  const [predictorVariableId, setPredictorVariableId] = useState(constructs[0]?.outputVariableId ?? '')
  const [outcomeVariableId, setOutcomeVariableId] = useState(constructs[1]?.outputVariableId ?? '')
  const [estimator, setEstimator] = useState<'ML' | 'WLSMV'>(model.estimation.estimator ?? 'ML')
  const [confidenceLevel, setConfidenceLevel] = useState(model.estimation.confidenceLevel || 0.95)
  const [missing, setMissing] = useState<'fiml' | 'complete_cases_per_model'>(
    model.estimation.missing === 'fiml' ? 'fiml' : 'complete_cases_per_model',
  )

  const distinct = Boolean(predictorVariableId && outcomeVariableId && predictorVariableId !== outcomeVariableId)
  const canApply = !disabled && constructs.length >= 2 && distinct

  return (
    <section className="context-method-runner" aria-labelledby="sem-quick-form-heading">
      <header>
        <p className="eyebrow">基础 SEM 表单</p>
        <h2 id="sem-quick-form-heading">两构念结构路径 X → Y</h2>
        <p className="muted">测量题项直接使用当前量表定义；这里仅指定结构路径与基础估计设置。应用后可在同页校验、冻结和运行。</p>
      </header>

      {constructs.length < 2 ? (
        <p className="error-message" role="alert">基础 SEM 至少需要两个已定义构念。请先在“数据 → 量表”建立测量版本。</p>
      ) : (
        <fieldset className="process-editing-fields" disabled={disabled}>
          <legend>结构与估计</legend>
          <div className="method-catalog-filters">
            <label>
              预测构念 X
              <select value={predictorVariableId} onChange={(event) => setPredictorVariableId(event.target.value)}>
                {constructs.map((construct) => (
                  <option key={construct.id} value={construct.outputVariableId}>{construct.name}</option>
                ))}
              </select>
            </label>
            <label>
              结果构念 Y
              <select value={outcomeVariableId} onChange={(event) => setOutcomeVariableId(event.target.value)}>
                {constructs.map((construct) => (
                  <option key={construct.id} value={construct.outputVariableId}>{construct.name}</option>
                ))}
              </select>
            </label>
            <label>
              估计器
              <select
                value={estimator}
                onChange={(event) => {
                  const next = event.target.value as 'ML' | 'WLSMV'
                  setEstimator(next)
                  if (next === 'WLSMV') setMissing('complete_cases_per_model')
                }}
              >
                <option value="ML">ML 最大似然</option>
                <option value="WLSMV">WLSMV 有序/分类指标</option>
              </select>
            </label>
            <label>
              置信水平
              <select value={String(confidenceLevel)} onChange={(event) => setConfidenceLevel(Number(event.target.value))}>
                <option value="0.9">90%</option>
                <option value="0.95">95%</option>
                <option value="0.99">99%</option>
              </select>
            </label>
            {estimator === 'ML' ? (
              <label>
                缺失数据
                <select value={missing} onChange={(event) => setMissing(event.target.value as typeof missing)}>
                  <option value="fiml">FIML</option>
                  <option value="complete_cases_per_model">完整案例</option>
                </select>
              </label>
            ) : null}
          </div>
        </fieldset>
      )}

      {!distinct && constructs.length >= 2 ? <p className="error-message" role="alert">预测构念与结果构念必须不同。</p> : null}
      {estimator === 'WLSMV' ? <p className="method-note">WLSMV 按现有 SEM 契约使用完整案例口径，不提供 FIML。</p> : null}
      <p className="method-note">应用表单只创建当前 SEM 草稿；不会自动运行，也不会改变现有量表定义。</p>

      <div className="analysis-inline-actions">
        <button
          type="button"
          className="run-button"
          disabled={!canApply}
          onClick={() => onApply({
            predictorVariableId,
            outcomeVariableId,
            estimator,
            confidenceLevel,
            missing: estimator === 'WLSMV' ? 'complete_cases_per_model' : missing,
          })}
        >
          应用 SEM 设置
        </button>
        <button type="button" className="secondary-button" onClick={onOpenAdvanced}>打开高级 SEM 编辑器</button>
      </div>
    </section>
  )
}
