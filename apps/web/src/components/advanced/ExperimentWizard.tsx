import type React from 'react'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

export interface ExperimentWizardSpec {
  family: 'experimental_design'
  designType: 'factorial_anova' | 'ancova' | 'repeated_measures' | 'mixed_design'
  dataLayout: 'long' | 'wide'
  outcomeIds: string[]
  betweenFactors: Array<{ variableId: string; coding: 'sum' | 'treatment' | 'helmert' }>
  withinFactors?: Array<{ factorName: string; levels: string[] }>
  covariates?: string[]
  sumOfSquares: 'II' | 'III'
  postHocAdjustment: 'holm' | 'bonferroni' | 'tukey' | 'games_howell'
  plannedContrasts?: Array<{ name: string; weights: number[] }>
  tostSesoi?: { lower: number; upper: number }
}

export interface ExperimentWizardProps {
  spec: ExperimentWizardSpec
  onChange: (spec: ExperimentWizardSpec) => void
  variables: DatasetVariableItem[]
}

export const ExperimentWizard: React.FC<ExperimentWizardProps> = ({ spec, onChange, variables }) => {
  const update = (patch: Partial<ExperimentWizardSpec>) => {
    onChange({ ...spec, ...patch })
  }

  return (
    <div className="adv-experiment-wizard-panel" style={{ padding: '16px', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
      <h3>实验设计与分析配置向导 (Experimental Design Wizard)</h3>
      <p className="muted">组间 1-3 因素 ANOVA/ANCOVA、单 Within 重复测量、计划对比及声明 family 内多重性校正。当前不生成 CONSORT 样本流。</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            实验设计类型 (Design Type)
            <select
              className="adv-select"
              value={spec.designType || 'factorial_anova'}
              onChange={e => update({ designType: e.target.value as ExperimentWizardSpec['designType'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="factorial_anova">析因 ANOVA (Factorial ANOVA)</option>
              <option value="ancova">协方差分析 (ANCOVA)</option>
              <option value="repeated_measures">重复测量 (Repeated Measures RM-ANOVA)</option>
              <option value="mixed_design">混合设计 (Mixed Design)</option>
            </select>
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            平方和类型 (Type SS)
            <select
              className="adv-select"
              value={spec.sumOfSquares || 'III'}
              onChange={e => update({ sumOfSquares: e.target.value as ExperimentWizardSpec['sumOfSquares'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="III">Type III SS (非平衡设计的默认规则)</option>
              <option value="II">Type II SS (无主效应交互时的平稳规则)</option>
            </select>
          </label>
        </div>
      </div>

      <div style={{ marginTop: '16px' }}>
        <DatasetVariablePicker
          label="因变量 / 结局 (Outcomes)"
          variables={variables.filter(v => v.type === 'numeric')}
          selectedIds={spec.outcomeIds || []}
          onChange={ids => update({ outcomeIds: ids })}
          isMulti={false}
          roleHint="选择1个连续变量作为实验结局"
        />
      </div>

      <div style={{ marginTop: '16px' }}>
        <DatasetVariablePicker
          label="组间因子 (Between Factors)"
          variables={variables.filter(v => v.type === 'categorical')}
          selectedIds={(spec.betweenFactors || []).map(f => f.variableId)}
          onChange={ids => update({ betweenFactors: ids.map(id => ({ variableId: id, coding: 'sum' })) })}
          isMulti={true}
          roleHint="选择分类处理/条件变量"
        />
      </div>

      {spec.designType === 'ancova' && (
        <div style={{ marginTop: '16px' }}>
          <DatasetVariablePicker
            label="控制协变量 (Pre-treatment Covariates)"
            variables={variables.filter(v => v.type === 'numeric')}
            selectedIds={spec.covariates || []}
            onChange={ids => update({ covariates: ids })}
            isMulti={true}
            roleHint="必须为随机化前/暴露前测量"
          />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            事后检验校正 (Post-hoc Adjustment)
            <select
              className="adv-select"
              value={spec.postHocAdjustment || 'holm'}
              onChange={e => update({ postHocAdjustment: e.target.value as ExperimentWizardSpec['postHocAdjustment'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="holm">Holm-Bonferroni 序贯校正</option>
              <option value="tukey">Tukey HSD 均值差校正</option>
              <option value="games_howell">Games-Howell 方差不齐事后校正</option>
              <option value="bonferroni">Bonferroni 严格多重性校正</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  )
}
