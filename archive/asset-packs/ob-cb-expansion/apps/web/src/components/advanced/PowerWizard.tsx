import type React from 'react'
import type { DatasetVariableItem } from './DatasetVariablePicker'

export interface PowerWizardSpec {
  family: 'power_analysis'
  designFamily: 'regression' | 'factorial_anova' | 't_test'
  solveFor: 'sample_size' | 'power' | 'effect_size' | 'target_precision'
  alpha: number
  targetPower?: number
  effectSize?: { metric: string; value: number }
  predictors?: number
  groups?: number
  alternative: 'two_sided' | 'one_sided'
  simulations?: number
  precisionWidth?: number
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

  return (
    <div className="adv-power-wizard-panel" style={{ padding: '16px', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
      <h3>功效、精度与敏感性分析配置向导 (Power & Precision Wizard)</h3>
      <p className="muted">按科研需求求解样本量 $N$、达致功效 $Power$、最小可检测效应 $MDES$ 或目标 CI 半宽 $Precision$。</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
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
              <option value="target_precision">求解目标 CI 宽度所需 N (Precision)</option>
            </select>
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            设计类型 (Design Family)
            <select
              className="adv-select"
              value={spec.designFamily || 'regression'}
              onChange={e => update({ designFamily: e.target.value as PowerWizardSpec['designFamily'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="regression">线性回归 (Regression f²)</option>
              <option value="factorial_anova">析因 ANOVA (Factorial f)</option>
              <option value="t_test">t 检验 (t-test Cohen's d)</option>
            </select>
          </label>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            显著性水平 ($\alpha$)
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
              目标功效 ($1 - \beta$)
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

      {spec.solveFor === 'target_precision' && (
        <div style={{ marginTop: '16px' }}>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            目标 CI 置信区间半宽 (Target Half-Width E)
            <input
              type="number"
              step="0.01"
              className="adv-input"
              value={spec.precisionWidth ?? 0.10}
              onChange={e => update({ precisionWidth: parseFloat(e.target.value) || 0.10 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>
      )}

      {spec.solveFor !== 'effect_size' && (
        <div style={{ marginTop: '16px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <div>
            <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              效应量指标 (Metric)
              <input
                type="text"
                className="adv-input"
                value={spec.effectSize?.metric || 'cohens_f2'}
                onChange={e => update({ effectSize: { metric: e.target.value, value: spec.effectSize?.value || 0.15 } })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
          <div>
            <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              预估效应量数值 (Value)
              <input
                type="number"
                step="0.01"
                className="adv-input"
                value={spec.effectSize?.value ?? 0.15}
                onChange={e => update({ effectSize: { metric: spec.effectSize?.metric || 'cohens_f2', value: parseFloat(e.target.value) || 0.15 } })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
        </div>
      )}
    </div>
  )
}
