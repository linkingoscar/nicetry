import type { DiaryMultilevelOptions } from '../../types'

interface Candidate {
  id: string
  label: string
}

interface DiaryComplianceWindowSectionProps {
  value: DiaryMultilevelOptions
  variables: Candidate[]
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryComplianceWindowSection({
  value,
  variables,
  onChange,
}: DiaryComplianceWindowSectionProps) {
  return (
    <fieldset className="analysis-config-subsection">
      <legend>依从性与有效响应窗口</legend>
      <div className="empirical-config-grid">
        <label>每人预期观测次数
          <input
            type="number"
            min="2"
            max="1000"
            value={value.expectedObservationsPerPerson ?? ''}
            onChange={(event) => onChange({
              expectedObservationsPerPerson: event.target.value === ''
                ? null
                : Number(event.target.value),
            })}
          />
        </label>
        <label>最低依从率
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={value.minimumComplianceRate}
            onChange={(event) => onChange({
              minimumComplianceRate: Number(event.target.value),
            })}
          />
        </label>
        <label>响应延迟变量
          <select
            value={value.responseLatencyVariableId ?? ''}
            onChange={(event) => onChange({
              responseLatencyVariableId: event.target.value || null,
            })}
          >
            <option value="">数据中没有响应延迟</option>
            {variables.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
            ))}
          </select>
        </label>
        {value.responseLatencyVariableId ? (
          <>
            <label>有效延迟下限
              <input
                type="number"
                min="0"
                value={value.minimumResponseLatency ?? ''}
                onChange={(event) => onChange({
                  minimumResponseLatency: event.target.value === ''
                    ? null
                    : Number(event.target.value),
                })}
              />
            </label>
            <label>有效延迟上限
              <input
                type="number"
                min="0"
                value={value.maximumResponseLatency ?? ''}
                onChange={(event) => onChange({
                  maximumResponseLatency: event.target.value === ''
                    ? null
                    : Number(event.target.value),
                })}
              />
            </label>
          </>
        ) : null}
      </div>
      <div className="analysis-inline-actions">
        <label>
          <input
            type="checkbox"
            checked={value.excludeLowCompliance}
            disabled={!value.expectedObservationsPerPerson || value.minimumComplianceRate <= 0}
            onChange={(event) => onChange({ excludeLowCompliance: event.target.checked })}
          />
          按上述事前规则排除低依从性被试
        </label>
        <label>
          <input
            type="checkbox"
            checked={value.excludeOutOfWindow}
            disabled={!value.responseLatencyVariableId}
            onChange={(event) => onChange({ excludeOutOfWindow: event.target.checked })}
          />
          排除有效窗口外响应
        </label>
      </div>
    </fieldset>
  )
}
