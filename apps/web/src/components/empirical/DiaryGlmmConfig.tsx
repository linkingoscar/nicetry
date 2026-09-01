import type { DiaryMultilevelOptions } from '../../types'

interface DiaryGlmmConfigProps {
  value: DiaryMultilevelOptions
  variables: Array<{ id: string; label: string }>
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryGlmmConfig({ value, variables, onChange }: DiaryGlmmConfigProps) {
  const excluded = new Set([
    value.subjectVariableId,
    value.timeVariableId,
    value.outcomeVariableId,
    value.predictorVariableId,
  ])
  return (
    <fieldset className="analysis-config-subsection">
      <legend>结局分布与聚类结构</legend>
      <div className="empirical-config-grid">
        {value.analysisType === 'glmm' ? (
          <label>结局分布
            <select
              value={value.outcomeFamily}
              onChange={(event) => onChange({
                outcomeFamily:
                  event.target.value as DiaryMultilevelOptions['outcomeFamily'],
                countModel: 'standard',
                zeroProcessPredictors: 'intercept_only',
                exposureVariableId: event.target.value === 'binomial'
                  ? null
                  : value.exposureVariableId,
              })}
            >
              <option value="binomial">二元 Logit</option>
              <option value="poisson">Poisson 计数</option>
              <option value="negative_binomial">负二项计数</option>
            </select>
          </label>
        ) : null}
        {value.analysisType === 'glmm' && ['poisson', 'negative_binomial'].includes(
          value.outcomeFamily,
        ) ? (
          <>
            <label>计数过程
              <select
                value={value.countModel}
                onChange={(event) => onChange({
                  countModel: event.target.value as DiaryMultilevelOptions['countModel'],
                  zeroProcessPredictors: event.target.value === 'standard'
                    ? 'intercept_only'
                    : value.zeroProcessPredictors,
                })}
              >
                <option value="standard">标准计数 GLMM</option>
                <option value="zero_inflated">零膨胀（结构零 + 计数）</option>
                <option value="hurdle">Hurdle（零门槛 + 正计数）</option>
              </select>
            </label>
            {value.countModel !== 'standard' ? (
              <label>零过程规格
                <select
                  value={value.zeroProcessPredictors}
                  onChange={(event) => onChange({
                    zeroProcessPredictors:
                      event.target.value as DiaryMultilevelOptions['zeroProcessPredictors'],
                  })}
                >
                  <option value="intercept_only">仅截距</option>
                  <option value="shared">与计数过程共享固定预测项</option>
                </select>
              </label>
            ) : null}
            <label>模拟诊断次数
              <input
                type="number"
                min="100"
                max="2000"
                step="50"
                value={value.distributionDiagnosticSimulations}
                onChange={(event) => onChange({
                  distributionDiagnosticSimulations: Number(event.target.value),
                })}
              />
            </label>
          </>
        ) : null}
        <label>聚类结构
          <select
            value={value.clusterStructure}
            onChange={(event) => onChange({
              clusterStructure:
                event.target.value as DiaryMultilevelOptions['clusterStructure'],
              crossClassVariableId: event.target.value === 'nested'
                ? null
                : value.crossClassVariableId,
            })}
          >
            <option value="nested">时点嵌套于被试</option>
            <option value="cross_classified">被试 × 场景交叉分类</option>
          </select>
        </label>
        {value.clusterStructure === 'cross_classified' ? (
          <label>交叉分类单元
            <select
              value={value.crossClassVariableId ?? ''}
              onChange={(event) => onChange({
                crossClassVariableId: event.target.value || null,
              })}
            >
              <option value="">选择场景/刺激/任务 ID</option>
              {variables.filter((candidate) => !excluded.has(candidate.id)).map((candidate) => (
                <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
              ))}
            </select>
          </label>
        ) : null}
        {value.analysisType === 'glmm' && ['poisson', 'negative_binomial'].includes(
          value.outcomeFamily,
        ) ? (
          <label>暴露量 offset（可选）
            <select
              value={value.exposureVariableId ?? ''}
              onChange={(event) => onChange({
                exposureVariableId: event.target.value || null,
              })}
            >
              <option value="">等暴露量，不使用 offset</option>
              {variables.filter((candidate) => !excluded.has(candidate.id)).map((candidate) => (
                <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
              ))}
            </select>
          </label>
        ) : null}
      </div>
      <p className="analysis-note">
        交叉分类结构同时估计被试和场景随机截距；二元效应以 OR、计数效应以 IRR 输出。
        平台只提供模拟诊断和候选模型比较，不会因零值较多而自动切换模型。
      </p>
    </fieldset>
  )
}
