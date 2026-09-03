import type React from 'react'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

export interface ExperimentWizardSpec {
  family: 'experimental_design'
  analysisType?: 'anova' | 'glm_cluster'
  designType: 'factorial_anova' | 'ancova' | 'repeated_measures' | 'mixed_design'
  dataLayout: 'long' | 'wide'
  outcomeIds: string[]
  betweenFactors: Array<{ variableId: string; coding: 'sum' | 'treatment' | 'helmert'; referenceLevel?: string | number | null }>
  withinFactors?: Array<{ id: string; name: string; levels: string[]; columns: Record<string, string> }>
  subjectId?: string | null
  covariateIds?: string[]
  sumOfSquares: 'II' | 'III'
  sphericityCorrection?: 'auto' | 'greenhouse_geisser' | 'huynh_feldt'
  postHocAdjustment: 'holm' | 'tukey' | 'games_howell' | 'benjamini_hochberg'
  plannedContrasts?: Array<{
    id: string
    factorVariableId: string
    weights: Record<string, number>
    multiplicityFamilyId: string
  }>
  covariateCentering?: 'grand_mean' | 'none'
  homogeneityOfSlopes?: 'check_and_warn' | 'ignore'
}

export interface ExperimentWizardProps {
  spec: ExperimentWizardSpec
  onChange: (spec: ExperimentWizardSpec) => void
  variables: DatasetVariableItem[]
  sliceId?: string
}

export function experimentDesignTypeForSlice(sliceId?: string): ExperimentWizardSpec['designType'] | undefined {
  if (sliceId?.includes('.factorial_anova.')) return 'factorial_anova'
  if (sliceId?.includes('.ancova.')) return 'ancova'
  if (sliceId?.includes('.repeated_measures.')) return 'repeated_measures'
  if (sliceId?.includes('.mixed_design.')) return 'mixed_design'
  return undefined
}

const DESIGN_LABELS: Record<ExperimentWizardSpec['designType'], string> = {
  factorial_anova: '组间析因方差分析',
  ancova: '组间协方差分析（ANCOVA）',
  repeated_measures: '重复测量分析',
  mixed_design: '混合设计分析',
}

function parseLevels(value: string): string[] {
  return Array.from(new Set(value.split(/[,，\n]/).map(level => level.trim()).filter(Boolean))).slice(0, 20)
}

export const ExperimentWizard: React.FC<ExperimentWizardProps> = ({ spec, onChange, variables, sliceId }) => {
  const update = (patch: Partial<ExperimentWizardSpec>) => onChange({ ...spec, ...patch })
  const lockedDesignType = experimentDesignTypeForSlice(sliceId)
  const designType = lockedDesignType ?? spec.designType
  const repeatedDesign = designType === 'repeated_measures' || designType === 'mixed_design'
  const hasBetweenFactors = designType !== 'repeated_measures'
  const numericVariables = variables.filter(variable => variable.type === 'numeric')
  const subjectCandidates = variables.filter(variable => variable.type !== 'datetime')
  const withinFactor = spec.withinFactors?.[0] ?? {
    id: 'time',
    name: '时间',
    levels: ['1', '2'],
    columns: {},
  }

  const updateWithinFactor = (patch: Partial<(typeof withinFactor)>) => {
    update({ withinFactors: [{ ...withinFactor, ...patch }] })
  }

  return (
    <div className="adv-experiment-wizard-panel" style={{ padding: '16px', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
      <h3>{DESIGN_LABELS[designType]}</h3>
      <p className="muted">当前方法类型由方法库锁定。这里只配置本方法实际需要的变量与推断设置；切换到其他设计请返回方法库选择对应方法。</p>

      <div className="adv-form-grid adv-form-grid-two" style={{ marginTop: '16px' }}>
        <label className="adv-field-label">
          因变量 / 结局
          <select
            className="adv-select"
            value={spec.outcomeIds?.[0] ?? ''}
            onChange={event => update({ outcomeIds: event.target.value ? [event.target.value] : [] })}
          >
            <option value="">请选择连续结果变量</option>
            {numericVariables.map(variable => (
              <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>
            ))}
          </select>
        </label>

        {designType !== 'repeated_measures' ? (
          <label className="adv-field-label">
            平方和类型
            <select
              className="adv-select"
              value={spec.sumOfSquares || 'III'}
              onChange={event => update({ sumOfSquares: event.target.value as ExperimentWizardSpec['sumOfSquares'] })}
            >
              <option value="III">Type III SS（默认，适合非平衡设计）</option>
              <option value="II">Type II SS</option>
            </select>
          </label>
        ) : null}
      </div>

      {hasBetweenFactors ? (
        <div style={{ marginTop: '16px' }}>
          <DatasetVariablePicker
            label={designType === 'mixed_design' ? '组间因子' : '组间处理 / 分组因子'}
            variables={variables.filter(variable => variable.type === 'categorical')}
            selectedIds={(spec.betweenFactors || []).map(factor => factor.variableId)}
            onChange={ids => update({ betweenFactors: ids.slice(0, 3).map(id => ({ variableId: id, coding: 'sum' })) })}
            isMulti
            roleHint={designType === 'mixed_design' ? '混合设计至少需要一个组间因子' : '当前支持 1–3 个组间因子'}
          />
        </div>
      ) : null}

      {designType === 'ancova' ? (
        <div style={{ marginTop: '16px' }}>
          <DatasetVariablePicker
            label="控制协变量（暴露前 / 随机化前）"
            variables={numericVariables.filter(variable => !spec.outcomeIds.includes(variable.id))}
            selectedIds={spec.covariateIds || []}
            onChange={covariateIds => update({ covariateIds })}
            isMulti
            roleHint="ANCOVA 至少需要一个协变量；请只使用有明确设计依据的前置协变量"
          />
          <div className="adv-form-grid adv-form-grid-two" style={{ marginTop: '12px' }}>
            <label className="adv-field-label">
              协变量中心化
              <select
                className="adv-select"
                value={spec.covariateCentering ?? 'grand_mean'}
                onChange={event => update({ covariateCentering: event.target.value as 'grand_mean' | 'none' })}
              >
                <option value="grand_mean">总体均值中心化</option>
                <option value="none">不中心化</option>
              </select>
            </label>
            <label className="adv-field-label">
              斜率同质性
              <select
                className="adv-select"
                value={spec.homogeneityOfSlopes ?? 'check_and_warn'}
                onChange={event => update({ homogeneityOfSlopes: event.target.value as 'check_and_warn' | 'ignore' })}
              >
                <option value="check_and_warn">检查并提示</option>
                <option value="ignore">不检查</option>
              </select>
            </label>
          </div>
        </div>
      ) : null}

      {repeatedDesign ? (
        <section className="adv-form-section" aria-label="组内重复测量设置" style={{ marginTop: '16px' }}>
          <div className="adv-form-grid adv-form-grid-two">
            <label className="adv-field-label">
              被试 ID
              <select className="adv-select" value={spec.subjectId ?? ''} onChange={event => update({ subjectId: event.target.value || null })}>
                <option value="">请选择被试 / 个体 ID</option>
                {subjectCandidates.map(variable => <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>)}
              </select>
            </label>
            <label className="adv-field-label">
              数据布局
              <select
                className="adv-select"
                value={spec.dataLayout ?? 'long'}
                onChange={event => {
                  const dataLayout = event.target.value as 'long' | 'wide'
                  update({
                    dataLayout,
                    withinFactors: [{
                      ...withinFactor,
                      columns: dataLayout === 'wide' ? withinFactor.columns : {},
                    }],
                  })
                }}
              >
                <option value="long">长格式</option>
                <option value="wide">宽格式</option>
              </select>
            </label>
            <label className="adv-field-label">
              组内因子名称
              <input className="adv-input" value={withinFactor.name} onChange={event => updateWithinFactor({ name: event.target.value })} />
            </label>
            <label className="adv-field-label">
              组内水平（逗号分隔）
              <input
                className="adv-input"
                value={withinFactor.levels.join(', ')}
                onChange={event => {
                  const levels = parseLevels(event.target.value)
                  updateWithinFactor({
                    levels,
                    columns: Object.fromEntries(levels.map(level => [level, withinFactor.columns[level] ?? ''])),
                  })
                }}
                placeholder="例如：T1, T2, T3"
              />
            </label>
          </div>

          {spec.dataLayout === 'wide' ? (
            <div className="adv-form-grid adv-form-grid-two" style={{ marginTop: '12px' }}>
              {withinFactor.levels.map(level => (
                <label className="adv-field-label" key={level}>
                  {level} 对应列
                  <select
                    className="adv-select"
                    value={withinFactor.columns[level] ?? ''}
                    onChange={event => updateWithinFactor({ columns: { ...withinFactor.columns, [level]: event.target.value } })}
                  >
                    <option value="">请选择该时间点变量</option>
                    {numericVariables.map(variable => <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>)}
                  </select>
                </label>
              ))}
            </div>
          ) : (
            <p className="muted">长格式的被试内水平由当前数据结构绑定；这里声明稳定的水平名称。宽格式时需要为每个水平显式选择对应列。</p>
          )}

          <label className="adv-field-label" style={{ marginTop: '12px' }}>
            球形性校正
            <select
              className="adv-select"
              value={spec.sphericityCorrection ?? 'auto'}
              onChange={event => update({ sphericityCorrection: event.target.value as NonNullable<ExperimentWizardSpec['sphericityCorrection']> })}
            >
              <option value="auto">自动判断</option>
              <option value="greenhouse_geisser">Greenhouse–Geisser</option>
              <option value="huynh_feldt">Huynh–Feldt</option>
            </select>
          </label>
        </section>
      ) : null}

      <div className="adv-form-grid adv-form-grid-two" style={{ marginTop: '16px' }}>
        <label className="adv-field-label">
          多重比较 / 事后校正
          <select
            className="adv-select"
            value={spec.postHocAdjustment || 'holm'}
            onChange={event => update({ postHocAdjustment: event.target.value as ExperimentWizardSpec['postHocAdjustment'] })}
          >
            <option value="holm">Holm 序贯校正</option>
            <option value="tukey">Tukey HSD</option>
            <option value="games_howell">Games–Howell（仅单一组间因子且无协变量）</option>
            <option value="benjamini_hochberg">Benjamini–Hochberg</option>
          </select>
        </label>
      </div>

      <p className="muted" style={{ marginTop: '12px' }}>计划对比和其他少用规格保留在“高级设置 → JSON”中；字段表单不会自动生成未经声明的对比。</p>
    </div>
  )
}
