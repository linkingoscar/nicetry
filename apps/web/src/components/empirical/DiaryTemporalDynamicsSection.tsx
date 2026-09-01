import type { DiaryMultilevelOptions } from '../../types'

interface Candidate {
  id: string
  label: string
}

interface DiaryTemporalDynamicsSectionProps {
  value: DiaryMultilevelOptions
  variables: Candidate[]
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryTemporalDynamicsSection({
  value,
  variables,
  onChange,
}: DiaryTemporalDynamicsSectionProps) {
  return (
    <fieldset className="analysis-config-subsection">
      <legend>时间动态与跨层效应</legend>
      <div className="empirical-config-grid">
        {value.analysisType !== 'bayesian_dsem' ? <label>时间效应
          <select
            value={value.temporalEffect}
            onChange={(event) => onChange({
              temporalEffect: event.target.value as DiaryMultilevelOptions['temporalEffect'],
            })}
          >
            <option value="contemporaneous">同时效应 Xₜ→Yₜ</option>
            <option value="lagged">滞后效应 Xₜ₋₁→Yₜ</option>
            {value.analysisType === 'lmm' || value.analysisType === 'glmm' ? (
              <option value="both">同时与滞后同时估计</option>
            ) : null}
          </select>
        </label> : null}
        {value.analysisType !== 'bayesian_dsem'
        && value.temporalEffect !== 'contemporaneous' ? (
          <>
            <label>滞后阶数
              <input
                type="number"
                min="1"
                max="10"
                value={value.lagOrder}
                onChange={(event) => onChange({ lagOrder: Number(event.target.value) })}
              />
            </label>
            <label>预期时间间隔
              <input
                type="number"
                min="0"
                step="0.1"
                value={value.expectedTimeInterval ?? ''}
                placeholder="留空则按相邻记录"
                onChange={(event) => onChange({
                  expectedTimeInterval: event.target.value === ''
                    ? null
                    : Number(event.target.value),
                })}
              />
            </label>
            <label>间隔容差
              <input
                type="number"
                min="0"
                step="0.1"
                value={value.timeIntervalTolerance}
                onChange={(event) => onChange({
                  timeIntervalTolerance: Number(event.target.value),
                })}
              />
            </label>
          </>
        ) : null}
        {value.analysisType !== 'bayesian_dsem' ? <label>Level 2 调节变量
          <select
            value={value.level2ModeratorVariableId ?? ''}
            onChange={(event) => onChange({
              level2ModeratorVariableId: event.target.value || null,
              level2CovariateIds: value.level2CovariateIds.filter(
                (id) => id !== event.target.value,
              ),
            })}
          >
            <option value="">不检验跨层调节</option>
            {variables.filter((candidate) => ![
              value.timeVariableId,
              value.outcomeVariableId,
              value.predictorVariableId,
              value.mediatorVariableId,
            ].includes(candidate.id)).map((candidate) => (
              <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
            ))}
          </select>
        </label> : null}
        <label>时间原点
          <select
            value={value.timeOriginStrategy}
            onChange={(event) => onChange({
              timeOriginStrategy:
                event.target.value as DiaryMultilevelOptions['timeOriginStrategy'],
              customTimeOrigin: event.target.value === 'custom'
                ? value.customTimeOrigin
                : null,
            })}
          >
            <option value="sample_mean">样本观测均值</option>
            <option value="first_observed">首个观测时点</option>
            <option value="custom">自定义原点</option>
          </select>
        </label>
        {value.timeOriginStrategy === 'custom' ? (
          <label>自定义时间原点
            <input
              type="number"
              step="any"
              value={value.customTimeOrigin ?? ''}
              onChange={(event) => onChange({
                customTimeOrigin: event.target.value === ''
                  ? null
                  : Number(event.target.value),
              })}
            />
          </label>
        ) : null}
      </div>
      <div className="analysis-inline-actions">
        <label>
          <input
            type="checkbox"
            checked={value.includeLinearTime}
            onChange={(event) => onChange({ includeLinearTime: event.target.checked })}
          />
          控制线性时间趋势
        </label>
        <label>
          <input
            type="checkbox"
            checked={value.includeQuadraticTime}
            onChange={(event) => onChange({
              includeQuadraticTime: event.target.checked,
              includeLinearTime: event.target.checked ? true : value.includeLinearTime,
            })}
          />
          控制二次时间趋势
        </label>
      </div>
      <p className="analysis-note">
        CWC 会把 Level-1 预测变量拆为组内偏差和按被试等权的个人均值成分；
        Level-2 调节变量采用按被试等权的 CGM。二次趋势与线性趋势联合进入并报告联合 Wald 检验。
      </p>
    </fieldset>
  )
}
