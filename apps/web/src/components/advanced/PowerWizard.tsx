import { useEffect } from 'react'
import type React from 'react'
import type { DatasetVariableItem } from './DatasetVariablePicker'

export interface PowerWizardSpec {
  family: 'power_analysis'
  method?: 'analytic' | 'monte_carlo'
  designFamily: 'regression' | 'factorial_anova' | 't_test'
  solveFor: 'sample_size' | 'power' | 'effect_size' | 'ci_width'
  alpha: number
  targetPower?: number
  sampleSize?: number
  effectSize?: { metric: string; value: number }
  effectSizeMetric?: string
  predictors?: number
  groups?: number
  alternative: 'two_sided' | 'one_sided'
  simulations?: number
  targetCIWidth?: number
  seed?: number
  [key: string]: unknown
}

export interface PowerWizardProps {
  spec: PowerWizardSpec
  onChange: (spec: PowerWizardSpec) => void
  variables?: DatasetVariableItem[]
  sliceId?: string
}

function effectMetricForDesign(designFamily: PowerWizardSpec['designFamily']) {
  if (designFamily === 'factorial_anova') return { id: 'cohens_f', label: "Cohen's f" }
  if (designFamily === 't_test') return { id: 'cohens_d', label: "Cohen's d" }
  return { id: 'cohens_f2', label: "Cohen's f²" }
}

export function powerDesignFamilyForSlice(sliceId?: string): PowerWizardSpec['designFamily'] | undefined {
  if (sliceId === 'power_analysis.analytic.regression') return 'regression'
  if (sliceId === 'power_analysis.analytic.factorial_anova') return 'factorial_anova'
  if (sliceId === 'power_analysis.analytic.t_test') return 't_test'
  // The current guided Monte Carlo template is a regression DGP. Other registered DGPs remain editable in advanced JSON.
  if (sliceId === 'power_analysis.monte_carlo') return 'regression'
  return undefined
}

function powerMethodForSlice(sliceId?: string): PowerWizardSpec['method'] | undefined {
  if (sliceId === 'power_analysis.monte_carlo') return 'monte_carlo'
  if (sliceId?.startsWith('power_analysis.analytic.')) return 'analytic'
  return undefined
}

export function normalizePowerSpecForSlice(spec: PowerWizardSpec, sliceId?: string): PowerWizardSpec {
  const lockedDesign = powerDesignFamilyForSlice(sliceId)
  const lockedMethod = powerMethodForSlice(sliceId)
  const designFamily = lockedDesign ?? spec.designFamily
  const designChanged = designFamily !== spec.designFamily
  const metric = effectMetricForDesign(designFamily)
  const method = lockedMethod ?? spec.method
  const monteCarlo = method === 'monte_carlo'
  const solveFor = monteCarlo && spec.solveFor === 'ci_width' ? 'sample_size' : spec.solveFor

  const next: PowerWizardSpec = {
    ...spec,
    ...(method ? { method } : {}),
    designFamily,
    solveFor,
    alternative: 'two_sided',
  }

  if (designChanged) next.groups = designFamily === 'regression' ? 1 : 2

  if (solveFor === 'power') {
    next.sampleSize = spec.sampleSize ?? 200
    next.targetCIWidth = undefined
    next.effectSize = { metric: metric.id, value: spec.effectSize?.value ?? 0.15 }
    next.effectSizeMetric = metric.id
  } else if (solveFor === 'effect_size') {
    next.sampleSize = spec.sampleSize ?? 200
    next.effectSize = undefined
    next.effectSizeMetric = metric.id
    next.targetCIWidth = undefined
  } else if (solveFor === 'ci_width') {
    next.sampleSize = undefined
    next.effectSize = undefined
    next.effectSizeMetric = undefined
    next.targetCIWidth = spec.targetCIWidth ?? 0.10
  } else {
    next.sampleSize = undefined
    next.targetCIWidth = undefined
    next.effectSize = { metric: metric.id, value: spec.effectSize?.value ?? 0.15 }
    next.effectSizeMetric = metric.id
  }

  return next
}

export const PowerWizard: React.FC<PowerWizardProps> = ({ spec, onChange, sliceId }) => {
  const normalizedSpec = normalizePowerSpecForSlice(spec, sliceId)
  const lockedDesign = powerDesignFamilyForSlice(sliceId)
  const monteCarlo = normalizedSpec.method === 'monte_carlo'

  useEffect(() => {
    if (JSON.stringify(normalizedSpec) !== JSON.stringify(spec)) onChange(normalizedSpec)
  }, [normalizedSpec, onChange, spec])

  const update = (patch: Partial<PowerWizardSpec>) => {
    onChange(normalizePowerSpecForSlice({ ...normalizedSpec, ...patch }, sliceId))
  }
  const effectMetric = effectMetricForDesign(normalizedSpec.designFamily)

  const updateSolveFor = (solveFor: PowerWizardSpec['solveFor']) => {
    const patch: Partial<PowerWizardSpec> = { solveFor }
    if (solveFor === 'power' || solveFor === 'effect_size') patch.sampleSize = normalizedSpec.sampleSize ?? 200
    if (solveFor === 'effect_size') {
      patch.effectSize = undefined
      patch.effectSizeMetric = effectMetric.id
    } else if (solveFor === 'ci_width') {
      patch.effectSize = undefined
      patch.targetCIWidth = normalizedSpec.targetCIWidth ?? 0.10
    } else {
      patch.effectSize = normalizedSpec.effectSize ?? { metric: effectMetric.id, value: 0.15 }
    }
    update(patch)
  }

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
              value={normalizedSpec.solveFor || 'sample_size'}
              onChange={e => updateSolveFor(e.target.value as PowerWizardSpec['solveFor'])}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="sample_size">求解所需样本量 N (A Priori Sample Size)</option>
              <option value="power">求解达致功效 Power (Achieved Power)</option>
              <option value="effect_size">求解最小可检测效应 MDES (Sensitivity)</option>
              {!monteCarlo ? <option value="ci_width">求解目标 CI 宽度所需 N (Precision)</option> : null}
            </select>
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            设计类型 (Design Family)
            <select
              className="adv-select"
              value={normalizedSpec.designFamily}
              disabled={Boolean(lockedDesign)}
              onChange={e => {
                const designFamily = e.target.value as PowerWizardSpec['designFamily']
                const metric = effectMetricForDesign(designFamily)
                update({
                  designFamily,
                  groups: designFamily === 'regression' ? 1 : 2,
                  effectSize: normalizedSpec.solveFor === 'effect_size' || normalizedSpec.solveFor === 'ci_width'
                    ? undefined
                    : { metric: metric.id, value: normalizedSpec.effectSize?.value ?? 0.15 },
                  effectSizeMetric: normalizedSpec.solveFor === 'effect_size' ? metric.id : normalizedSpec.effectSizeMetric,
                })
              }}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="regression">线性回归 (Regression f²)</option>
              <option value="factorial_anova">析因 ANOVA (Factorial f)</option>
              <option value="t_test">t 检验 (t-test Cohen's d)</option>
            </select>
          </label>
          {lockedDesign ? (
            <small className="adv-field-help">
              当前设计由方法库入口锁定；{monteCarlo ? '其他 Monte Carlo DGP 可在高级 JSON 中配置。' : '切换设计请返回方法库选择对应功效方法。'}
            </small>
          ) : null}
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
              value={normalizedSpec.alpha ?? 0.05}
              onChange={e => update({ alpha: parseFloat(e.target.value) || 0.05 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>

        {normalizedSpec.solveFor !== 'power' && (
          <div>
            <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
              目标统计功效（1 − β）
              <input
                type="number"
                step="0.05"
                className="adv-input"
                value={normalizedSpec.targetPower ?? 0.80}
                onChange={e => update({ targetPower: parseFloat(e.target.value) || 0.80 })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
        )}

        <div>
          <span className="adv-field-label">检验方向</span>
          <strong className="adv-readonly-value">双侧检验 (Two-sided)</strong>
          <small className="adv-field-help">当前已登记的功效契约不接受缺少方向参数的单侧提交。</small>
        </div>
      </div>

      {(normalizedSpec.solveFor === 'power' || normalizedSpec.solveFor === 'effect_size') ? (
        <div className="adv-form-section">
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            当前总样本量 N
            <input
              type="number"
              min="4"
              step="1"
              className="adv-input"
              value={normalizedSpec.sampleSize ?? 200}
              onChange={e => update({ sampleSize: Math.max(4, Math.round(Number(e.target.value) || 4)) })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
          <small className="adv-field-help">求解达成功效或最小可检测效应时，需要给定当前样本量。</small>
        </div>
      ) : null}

      {normalizedSpec.solveFor === 'ci_width' && (
        <div className="adv-form-section">
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            目标置信区间半宽
            <input
              type="number"
              step="0.01"
              className="adv-input"
              value={normalizedSpec.targetCIWidth ?? 0.10}
              onChange={e => update({ targetCIWidth: parseFloat(e.target.value) || 0.10 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>
      )}

      {normalizedSpec.solveFor !== 'effect_size' && normalizedSpec.solveFor !== 'ci_width' && (
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
                value={normalizedSpec.effectSize?.value ?? 0.15}
                onChange={e => update({ effectSize: { metric: effectMetric.id, value: parseFloat(e.target.value) || 0.15 } })}
                style={{ width: '100%', padding: '6px', marginTop: '4px' }}
              />
            </label>
          </div>
        </div>
      )}

      {normalizedSpec.solveFor === 'effect_size' ? (
        <p className="muted">将使用 {effectMetric.label} 作为 MDES 指标；提交时不携带已知效应量值。</p>
      ) : null}
    </div>
  )
}
