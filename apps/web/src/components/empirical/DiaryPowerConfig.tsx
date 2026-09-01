import type { DiaryPowerOptions } from '../../types'
import { parseIntegerGrid } from './powerAnalysisConfigUtils'

export const DEFAULT_DIARY_POWER: DiaryPowerOptions = {
  personCounts: [50, 80, 120],
  observationsPerPerson: [7, 10, 14],
  replications: 500,
  targetPower: 0.8,
  alpha: 0.05,
  withinEffect: 0.15,
  betweenEffect: 0.2,
  randomInterceptSd: 0.5,
  randomSlopeSd: 0.1,
  residualSd: 1,
  predictorBetweenSd: 0.7,
  predictorWithinSd: 1,
  residualAr1: 0.2,
  seed: 20260714,
}

interface DiaryPowerConfigProps {
  value: DiaryPowerOptions | null
  onChange: (value: DiaryPowerOptions | null) => void
}

export function DiaryPowerConfig({ value, onChange }: DiaryPowerConfigProps) {
  const update = (patch: Partial<DiaryPowerOptions>) => {
    if (value) onChange({ ...value, ...patch })
  }
  return (
    <fieldset className="analysis-config-subsection">
      <legend>事前蒙特卡洛功效分析（人数 × 测量次数）</legend>
      <label className="analysis-inline-checkbox">
        <input
          type="checkbox"
          checked={value !== null}
          onChange={(event) => onChange(event.target.checked ? DEFAULT_DIARY_POWER : null)}
        />
        模拟当前随机效应与时间结构下的个体内主效应功效
      </label>
      {value ? (
        <div className="empirical-config-grid">
          <label>候选人数
            <input
              key={value.personCounts.join(',')}
              defaultValue={value.personCounts.join(', ')}
              onBlur={(event) => {
                const personCounts = parseIntegerGrid(event.target.value, 20)
                if (personCounts.length) update({ personCounts })
              }}
            />
          </label>
          <label>每人候选测量次数
            <input
              key={value.observationsPerPerson.join(',')}
              defaultValue={value.observationsPerPerson.join(', ')}
              onBlur={(event) => {
                const observationsPerPerson = parseIntegerGrid(event.target.value, 3)
                if (observationsPerPerson.length) update({ observationsPerPerson })
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
          <label>个体内预期效应
            <input
              type="number"
              step="0.01"
              value={value.withinEffect}
              onChange={(event) => update({ withinEffect: Number(event.target.value) })}
            />
          </label>
          <label>个体间预期效应
            <input
              type="number"
              step="0.01"
              value={value.betweenEffect}
              onChange={(event) => update({ betweenEffect: Number(event.target.value) })}
            />
          </label>
          <label>随机截距 SD
            <input
              type="number"
              min="0"
              step="0.05"
              value={value.randomInterceptSd}
              onChange={(event) => update({
                randomInterceptSd: Number(event.target.value),
              })}
            />
          </label>
          <label>随机斜率 SD
            <input
              type="number"
              min="0"
              step="0.05"
              value={value.randomSlopeSd}
              onChange={(event) => update({
                randomSlopeSd: Number(event.target.value),
              })}
            />
          </label>
          <label>残差 SD
            <input
              type="number"
              min="0.01"
              step="0.05"
              value={value.residualSd}
              onChange={(event) => update({ residualSd: Number(event.target.value) })}
            />
          </label>
          <label>残差 AR(1)
            <input
              type="number"
              min="-0.99"
              max="0.99"
              step="0.05"
              value={value.residualAr1}
              onChange={(event) => update({ residualAr1: Number(event.target.value) })}
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
      ) : null}
    </fieldset>
  )
}
