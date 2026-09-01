import type React from 'react'
import type { DatasetVariableItem } from './DatasetVariablePicker'

export interface PowerWizardSpec {
  family: 'power_analysis'
  designFamily: 'regression' | 'factorial_anova' | 't_test'
  solveFor: 'sample_size' | 'power' | 'effect_size' | 'ci_width'
  alpha: number
  targetPower?: number
  effectSize?: { metric: string; value: number }
  predictors?: number
  groups?: number
  alternative: 'two_sided' | 'one_sided'
  simulations?: number
  targetCIWidth?: number
  seed?: number
}

export interface PowerWizardProps {
  spec: PowerWizardSpec
  onChange: (spec: PowerWizardSpec) => void
  variables?: DatasetVariableItem[]
}

export const PowerWizard: React.FC<PowerWizardProps> = ({ spec, onChange }) => {
  const update = (patch: Partial<PowerWizardSpec>) => {
    onChange({ ...spec, ...patch })
  }
  const effectMetric = spec.designFamily === 'factorial_anova'
    ? { id: 'cohens_f', label: "Cohen's f" }
    : spec.designFamily === 't_test'
      ? { id: 'cohens_d', label: "Cohen's d" }
      : { id: 'cohens_f2', label: "Cohen's f²" }

  return (
    <div className="adv-power-wizard-panel">
      <h3>功效、精度与敏感性分析</h3>
      <p className="muted">按研究问题求解样本量 N、达成的统计功效、最小可检测效应（MDES）或目标置信区间半宽。</p>

      <div className="adv-form-grid adv-form-grid-two">
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            求解目标 (Solve For)
            <select
              className="adv-select"
              value={spec.solveFor || 'sample_size'}
              onChange={e => update({ solveFor: e.target.value as PowerWizardSpec['solveFor'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="sample_size">求解所需样本量 N (A Priori Sample Size)</option>
              <option value="power">求解达致功效 Power (Achieved Power)</option>
              <option value="effect_size">求解最小可检测效应 MDES (Sensitivity)</option>
              <option value="ci_width">求解目标 CI 宽度所需 N (Precision)</option>
            </select>
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            设计类型 (Design Family)
            <select
              className="adv-select"
              value={spec.designFamily || 'regression'}
              onChange={e => {
                const designFamily = e.target.value as PowerWizardSpec['designFamily']
                const metric = designFamily === 'factorial_anova'
                  ? 'cohens_f'
                  : designFamily === 't_test'
                    ? 'cohens_d'
                    : 'cohens_f2'
                update({
                  designFamily,
                  effectSize: { metric, value: spec.effectSize?.value ?? 0.15 },
                })
              }}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="regression">线性回归 (Regression f²)</option>
              <option value="factorial_anova">析因 ANOVA (Factorial f)</option>
              <option value="t_test">t 检验 (t-test Cohen's d)</option>
            </select>
          </label>
        </div>
      </div>

      <div className="adv-form-grid adv-form-grid-three">
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            显著性水平 α
            <input
              type="number"
              step="0.01"
              className="adv-input"
              value={spec.alpha ?? 0.05}
              onChange={e => update({ alpha: parseFloat(e.target.value) || 0.05 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>

        {spec.solveFor !== 'power' && (
          <div>
            <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              目标统计功效（1 − β）
              <input
                type="number"
                step="0.05"
                className="adv-input"
                value={spec.targetPower ?? 0.80}
                onChange={e => update({ targetPower: parseFloat(e.target.value) || 0.80 })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
        )}

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            尾性 (Alternative)
            <select
              className="adv-select"
              value={spec.alternative || 'two_sided'}
              onChange={e => update({ alternative: e.target.value as PowerWizardSpec['alternative'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="two_sided">双侧检验 (Two-sided)</option>
              <option value="one_sided">单侧检验 (One-sided)</option>
            </select>
          </label>
        </div>
      </div>

      {spec.solveFor === 'ci_width' && (
        <div className="adv-form-section">
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            目标置信区间半宽
            <input
              type="number"
              step="0.01"
              className="adv-input"
              value={spec.targetCIWidth ?? 0.10}
              onChange={e => update({ targetCIWidth: parseFloat(e.target.value) || 0.10 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>
      )}

      {spec.solveFor !== 'effect_size' && (
        <div className="adv-form-grid adv-form-grid-two">
          <div>
            <span className="adv-field-label">效应量指标</span>
            <strong className="adv-readonly-value">{effectMetric.label}</strong>
            <small className="adv-field-help">由设计类型自动匹配，避免提交内部枚举值。</small>
          </div>
          <div>
            <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              预估效应量数值 (Value)
              <input
                type="number"
                step="0.01"
                className="adv-input"
                value={spec.effectSize?.value ?? 0.15}
                onChange={e => update({ effectSize: { metric: effectMetric.id, value: parseFloat(e.target.value) || 0.15 } })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
