import { ResponseSurfaceSelector } from './ResponseSurfaceSelector'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import { ProcedureVariablePicker } from './ProcedureVariablePicker'

export function EmpiricalRegressionSection() {
  const {
    config: value,
    onConfigChange: onChange,
    analysisCandidates: scores,
  } = useEmpiricalAnalysisContext()

  const updateOutcome = (next: string | null) => {
    onChange({
      outcomeVariableId: next,
      controlVariableIds: value.controlVariableIds.filter((id) => id !== next),
      predictorVariableIds: next
        ? value.predictorVariableIds.filter((id) => id !== next)
        : value.predictorVariableIds,
      responseSurfacePredictorIds: next
        ? value.responseSurfacePredictorIds.filter((id) => id !== next)
        : value.responseSurfacePredictorIds,
    })
  }
  const focalIds = value.procedure === 'response_surface' ? value.responseSurfacePredictorIds : value.predictorVariableIds

  return (
    <details className="analysis-config-section" open>
      <summary><strong>模型变量</strong><small>按角色指定变量</small></summary>
      <div className="empirical-config-grid regression-config-grid">
        <label>因变量（Y）
          <select value={value.outcomeVariableId ?? ''} onChange={(event) => updateOutcome(event.target.value || null)}>
            <option value="">请选择因变量</option>
            {scores.map((score) => <option key={score.id} value={score.id}>{score.label}</option>)}
          </select>
        </label>
      </div>
      {value.outcomeVariableId ? (
        <>
          {['regression', 'relative_importance'].includes(value.procedure) ? <ProcedureVariablePicker label="区块 2：预测变量"
            candidates={scores.filter((score) => score.id !== value.outcomeVariableId && !value.controlVariableIds.includes(score.id))}
            selected={value.predictorVariableIds} onChange={(predictorVariableIds) => onChange({ predictorVariableIds })} /> : null}
          <ProcedureVariablePicker label="区块 1：控制变量（可选）"
            candidates={scores.filter((variable) => variable.id !== value.outcomeVariableId && !focalIds.includes(variable.id))}
            selected={value.controlVariableIds} onChange={(controlVariableIds) => onChange({ controlVariableIds })} />
          {value.procedure === 'response_surface' ? <ResponseSurfaceSelector
            scores={scores.filter((score) => !value.controlVariableIds.includes(score.id))}
            outcomeVariableId={value.outcomeVariableId}
            value={value.responseSurfacePredictorIds}
            onChange={(responseSurfacePredictorIds) => onChange({ responseSurfacePredictorIds })}
          /> : null}
        </>
      ) : <p className="method-note">选择结果变量后再配置预测、控制与响应面，未配置的分析不会生成空结果区。</p>}
    </details>
  )
}
