import type { LongitudinalPowerOptions } from '../../types'
import { parseIntegerGrid } from './powerAnalysisConfigUtils'

const DEFAULT_LONGITUDINAL_POWER: LongitudinalPowerOptions = {
  sampleSizes: [200, 300, 500, 800],
  replications: 500,
  targetPower: 0.8,
  alpha: 0.05,
  autoregressiveX: 0.4,
  autoregressiveY: 0.4,
  crossLaggedXToY: 0.1,
  crossLaggedYToX: 0.1,
  icc: 0.4,
  randomInterceptCorrelation: 0.3,
  withinCorrelation: 0.2,
  reliability: 0.8,
  estimateMeasurementError: false,
  seed: 20260714,
}

interface LongitudinalPowerConfigProps {
  value: LongitudinalPowerOptions | null
  onChange: (value: LongitudinalPowerOptions | null) => void
}

export function LongitudinalPowerConfig({
  value,
  onChange,
}: LongitudinalPowerConfigProps) {
  const update = (patch: Partial<LongitudinalPowerOptions>) => {
    if (value) onChange({ ...value, ...patch })
  }
  return (
    <fieldset className="analysis-config-subsection">
      <legend>事前蒙特卡洛功效分析（RI-CLPM）</legend>
      <label className="analysis-inline-checkbox">
        <input
          type="checkbox"
          checked={value !== null}
          onChange={(event) => onChange(event.target.checked
            ? DEFAULT_LONGITUDINAL_POWER
            : null)}
        />
        估计双向交叉滞后路径的功效、偏差与覆盖率
      </label>
      {value ? (
        <>
          <div className="empirical-config-grid">
            <label>候选样本量（逗号分隔）
              <input
                key={value.sampleSizes.join(',')}
                defaultValue={value.sampleSizes.join(', ')}
                onBlur={(event) => {
                  const sampleSizes = parseIntegerGrid(event.target.value, 50)
                  if (sampleSizes.length) update({ sampleSizes })
                }}
              />
            </label>
            <label>模拟重复次数
              <input
                type="number"
                min="20"
                max="5000"
                value={value.replications}
                onChange={(event) => update({ replications: Number(event.target.value) })}
              />
            </label>
            <label>目标功效
              <input
                type="number"
                min="0.5"
                max="0.99"
                step="0.01"
                value={value.targetPower}
                onChange={(event) => update({ targetPower: Number(event.target.value) })}
              />
            </label>
            <label>显著性水平 α
              <input
                type="number"
                min="0.001"
                max="0.2"
                step="0.001"
                value={value.alpha}
                onChange={(event) => update({ alpha: Number(event.target.value) })}
              />
            </label>
            <label>X→Y 预期效应
              <input
                type="number"
                step="0.01"
                value={value.crossLaggedXToY}
                onChange={(event) => update({
                  crossLaggedXToY: Number(event.target.value),
                })}
              />
            </label>
            <label>Y→X 预期效应
              <input
                type="number"
                step="0.01"
                value={value.crossLaggedYToX}
                onChange={(event) => update({
                  crossLaggedYToX: Number(event.target.value),
                })}
              />
            </label>
            <label>X / Y 自回归效应
              <span className="analysis-inline-actions">
                <input
                  aria-label="X 自回归效应"
                  type="number"
                  step="0.05"
                  value={value.autoregressiveX}
                  onChange={(event) => update({
                    autoregressiveX: Number(event.target.value),
                  })}
                />
                <input
                  aria-label="Y 自回归效应"
                  type="number"
                  step="0.05"
                  value={value.autoregressiveY}
                  onChange={(event) => update({
                    autoregressiveY: Number(event.target.value),
                  })}
                />
              </span>
            </label>
            <label>ICC
              <input
                type="number"
                min="0.01"
                max="0.99"
                step="0.05"
                value={value.icc}
                onChange={(event) => update({ icc: Number(event.target.value) })}
              />
            </label>
            <label>随机截距相关
              <input
                type="number"
                min="-0.99"
                max="0.99"
                step="0.05"
                value={value.randomInterceptCorrelation}
                onChange={(event) => update({
                  randomInterceptCorrelation: Number(event.target.value),
                })}
              />
            </label>
            <label>时点内 X–Y 相关
              <input
                type="number"
                min="-0.99"
                max="0.99"
                step="0.05"
                value={value.withinCorrelation}
                onChange={(event) => update({
                  withinCorrelation: Number(event.target.value),
                })}
              />
            </label>
            <label>测量信度
              <input
                type="number"
                min="0.1"
                max="1"
                step="0.05"
                value={value.reliability}
                onChange={(event) => update({ reliability: Number(event.target.value) })}
              />
            </label>
            <label>随机种子
              <input
                type="number"
                min="1"
                value={value.seed}
                onChange={(event) => update({ seed: Number(event.target.value) })}
              />
            </label>
          </div>
          <label className="analysis-inline-checkbox">
            <input
              type="checkbox"
              checked={value.estimateMeasurementError}
              onChange={(event) => update({
                estimateMeasurementError: event.target.checked,
              })}
            />
            在生成与估计模型中显式估计测量误差（STARTS 型设定）
          </label>
        </>
      ) : null}
    </fieldset>
  )
}
