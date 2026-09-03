import type { DiaryMultilevelOptions } from '../../types'
import { DiaryTemporalQualityConfig } from './DiaryTemporalQualityConfig'
import { DiaryAdvancedModelConfig } from './DiaryAdvancedModelConfig'
import type { LongitudinalItemGroup } from './LongitudinalPanelConfig'
import {
  createDiaryMultilevelDefault,
  diaryAnalysisTypePatch,
  DiaryAnalysisTypeSelect,
  DiaryVariableSelect,
  type DiaryCandidate,
} from './DiaryMultilevelConfigSections'
import {
  lockedDiaryAnalysisType,
  useEmpiricalMethodSliceId,
} from './EmpiricalMethodScopeContext'

interface DiaryMultilevelConfigProps {
  value: DiaryMultilevelOptions | null
  variables: DiaryCandidate[]
  itemGroups: LongitudinalItemGroup[]
  subjectCandidates: DiaryCandidate[]
  defaultSubjectId?: string | null
  defaultTimeId?: string | null
  onChange: (value: DiaryMultilevelOptions | null) => void
}

const ANALYSIS_TYPE_LABELS: Record<DiaryMultilevelOptions['analysisType'], string> = {
  lmm: '二层线性混合模型',
  glmm: '二元 / 计数广义多层模型',
  mediation: '多层中介',
  bayesian_dsem: 'Bayesian DSEM',
}

export function DiaryMultilevelConfig({
  value,
  variables,
  itemGroups,
  subjectCandidates,
  defaultSubjectId,
  defaultTimeId,
  onChange,
}: DiaryMultilevelConfigProps) {
  const methodSliceId = useEmpiricalMethodSliceId()
  const lockedAnalysisType = lockedDiaryAnalysisType(methodSliceId)
  const update = (patch: Partial<DiaryMultilevelOptions>) => {
    if (value) onChange({ ...value, ...patch })
  }
  const createForCurrentMethod = () => {
    const base = createDiaryMultilevelDefault(subjectCandidates, defaultSubjectId, defaultTimeId)
    if (!lockedAnalysisType || base.analysisType === lockedAnalysisType) return base
    return { ...base, ...diaryAnalysisTypePatch(base, lockedAnalysisType) }
  }

  return (
    <div className="diary-multilevel-config">
      <label className="analysis-feature-toggle">
        <input
          type="checkbox"
          checked={value !== null}
          onChange={(event) => onChange(
            event.target.checked ? createForCurrentMethod() : null,
          )}
        />
        <span>
          <strong>启用日记研究二层模型</strong>
          <small>重复日/时点嵌套于被试，支持随机斜率、AR(1)、多层中介与 DSEM。</small>
        </span>
      </label>
      {value ? (
        <>
          <div className="empirical-config-grid">
            {lockedAnalysisType ? (
              <div className="method-note" role="status">
                <strong>分析类型：{ANALYSIS_TYPE_LABELS[lockedAnalysisType]}</strong>
                <span>由方法库选择锁定；如需切换模型，请返回“分析方法”选择另一方法。</span>
              </div>
            ) : <DiaryAnalysisTypeSelect value={value} onChange={update} />}
            <DiaryVariableSelect
              label="被试 ID"
              value={value.subjectVariableId}
              options={subjectCandidates}
              disabled={Boolean(defaultSubjectId)}
              placeholder="选择被试 ID"
              onChange={(subjectVariableId) => update({ subjectVariableId })}
            />
            <DiaryVariableSelect
              label="日/时间变量"
              value={value.timeVariableId}
              options={variables}
              disabled={Boolean(defaultTimeId)}
              placeholder="选择时间变量"
              onChange={(timeVariableId) => update({ timeVariableId })}
            />
            <DiaryVariableSelect
              label="预测变量 X"
              value={value.predictorVariableId}
              options={variables}
              placeholder="选择 X"
              onChange={(predictorVariableId) => update({ predictorVariableId })}
            />
            <DiaryVariableSelect
              label="结果变量 Y"
              value={value.outcomeVariableId}
              options={variables}
              placeholder="选择 Y"
              onChange={(outcomeVariableId) => update({ outcomeVariableId })}
            />
            {value.analysisType === 'mediation' ? (
              <>
                <label>中介变量 M
                  <select
                    value={value.mediatorVariableId ?? ''}
                    onChange={(event) => update({ mediatorVariableId: event.target.value || null })}
                  >
                    <option value="">选择 M</option>
                    {variables.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
                    ))}
                  </select>
                </label>
                <label>中介结构
                  <select
                    value={value.mediationType}
                    onChange={(event) => {
                      const mediationType = event.target.value as DiaryMultilevelOptions['mediationType']
                      update({
                        mediationType,
                        centering: mediationType === '2-1-1' ? 'none' : 'person_mean',
                      })
                    }}
                  >
                    <option value="1-1-1">1-1-1：X/M/Y 均为日水平</option>
                    <option value="2-1-1">2-1-1：X 为人水平</option>
                  </select>
                </label>
              </>
            ) : value.analysisType !== 'bayesian_dsem' ? (
              <>
                {value.analysisType === 'lmm' ? <label>时间残差
                  <select
                    value={value.residualStructure}
                    onChange={(event) => update({
                      residualStructure: event.target.value as DiaryMultilevelOptions['residualStructure'],
                    })}
                  >
                    <option value="independent">独立残差</option>
                    <option value="ar1">AR(1) 自相关</option>
                  </select>
                </label> : null}
                <label>中心化
                  <select
                    value={value.centering}
                    onChange={(event) => update({
                      centering: event.target.value as DiaryMultilevelOptions['centering'],
                    })}
                  >
                    <option value="person_mean">人均中心化（分解 within/between）</option>
                    <option value="grand_mean">总均值中心化</option>
                    <option value="none">不中心化</option>
                  </select>
                </label>
              </>
            ) : null}
          </div>
          {value.analysisType === 'lmm' || value.analysisType === 'glmm' ? (
            <label className="analysis-inline-checkbox">
              <input
                type="checkbox"
                checked={value.randomSlope}
                onChange={(event) => update({ randomSlope: event.target.checked })}
              />
              允许 X 的被试间随机斜率
            </label>
          ) : null}
          <DiaryAdvancedModelConfig value={value} variables={variables} onChange={update} />
          {value.analysisType !== 'bayesian_dsem' ? <fieldset className="analysis-variable-picker">
            <legend>Level 2 被试层协变量（可选）</legend>
            {variables.filter((candidate) => ![
              value.timeVariableId,
              value.outcomeVariableId,
              value.predictorVariableId,
              value.mediatorVariableId,
            ].includes(candidate.id)).map((candidate) => (
              <label key={candidate.id}>
                <input
                  type="checkbox"
                  checked={value.level2CovariateIds.includes(candidate.id)}
                  onChange={() => update({
                    level2ModeratorVariableId: value.level2ModeratorVariableId === candidate.id
                      ? null
                      : value.level2ModeratorVariableId,
                    level2CovariateIds: value.level2CovariateIds.includes(candidate.id)
                      ? value.level2CovariateIds.filter((id) => id !== candidate.id)
                      : [...value.level2CovariateIds, candidate.id],
                  })}
                />
                {candidate.label}
              </label>
            ))}
          </fieldset> : null}
          <DiaryTemporalQualityConfig
            value={value}
            variables={variables}
            itemGroups={itemGroups}
            onChange={update}
          />
          <p className="method-note">
            人均中心化会显式生成 X 的个体内偏差和个体均值成分。多层中介分别报告 within-person 与 between-person 间接效应。
          </p>
        </>
      ) : null}
    </div>
  )
}
