import type { LongitudinalPanelOptions } from '../../types'
import { LongitudinalPowerConfig } from './PowerAnalysisConfig'
import type { LongitudinalPanelConfigProps } from './LongitudinalPanelConfig.types'
import { createDefaultPanel, createEmptyWaves } from './LongitudinalPanelConfig.utils'
import { LongitudinalConfigFields } from './LongitudinalConfigFields'
import { LongitudinalWaveTable } from './LongitudinalWaveTable'
import { PartialInvarianceFieldset } from './PartialInvarianceFieldset'
import {
  lockedLongitudinalModelType,
  useEmpiricalMethodSliceId,
} from './EmpiricalMethodScopeContext'

export type { LongitudinalItemGroup } from './LongitudinalPanelConfig.types'

export function LongitudinalPanelConfig({
  value,
  variables,
  itemGroups,
  subjectCandidates,
  defaultSubjectId,
  defaultWaveCount,
  onChange,
}: LongitudinalPanelConfigProps) {
  const methodSliceId = useEmpiricalMethodSliceId()
  const lockedModelType = lockedLongitudinalModelType(methodSliceId)
  const update = (patch: Partial<LongitudinalPanelOptions>) => {
    if (value) onChange({ ...value, ...patch })
  }
  const createPanelForCurrentMethod = () => {
    const base = createDefaultPanel(subjectCandidates, defaultSubjectId, defaultWaveCount)
    if (!lockedModelType) return base
    const minimum = lockedModelType === 'lcm_sr' ? 5 : lockedModelType === 'ri_clpm' ? 3 : 2
    return {
      ...base,
      modelType: lockedModelType,
      waves: base.waves.length < minimum
        ? [...base.waves, ...createEmptyWaves(minimum).slice(base.waves.length)]
        : base.waves,
      measurementMode: lockedModelType === 'lcm_sr' ? 'latent_items' as const : base.measurementMode,
      growthShape: lockedModelType === 'lcm_sr' ? base.growthShape : 'linear' as const,
      powerAnalysis: lockedModelType === 'ri_clpm' ? base.powerAnalysis : null,
    }
  }
  const updateWave = (
    index: number,
    patch: Partial<LongitudinalPanelOptions['waves'][number]>,
  ) => {
    if (!value) return
    const waves = value.waves.map((wave, waveIndex) => (
      waveIndex === index ? { ...wave, ...patch } : wave
    ))
    onChange({ ...value, waves })
  }
  const positionCounts = value
    ? {
        x: value.waves.find((wave) => wave.xItemIds.length)?.xItemIds.length ?? 0,
        y: value.waves.find((wave) => wave.yItemIds.length)?.yItemIds.length ?? 0,
      }
    : { x: 0, y: 0 }
  const togglePartialPosition = (position: string) => {
    if (!value) return
    update({
      partialInvariancePositions: value.partialInvariancePositions.includes(position)
        ? value.partialInvariancePositions.filter((entry) => entry !== position)
        : [...value.partialInvariancePositions, position],
    })
  }

  return (
    <div className="longitudinal-config">
      <label className="analysis-feature-toggle">
        <input
          type="checkbox"
          checked={value !== null}
          onChange={(event) => onChange(
            event.target.checked ? createPanelForCurrentMethod() : null,
          )}
        />
        <span>
          <strong>启用纵向面板分析</strong>
          <small>传统 CLPM 支持两时点；RI-CLPM 至少三时点；LCM-SR 至少五时点。</small>
        </span>
      </label>
      {value ? (
        <>
          <LongitudinalConfigFields
            value={value}
            subjectCandidates={subjectCandidates}
            defaultSubjectId={defaultSubjectId}
            onChange={onChange}
            update={update}
          />
          <LongitudinalWaveTable
            value={value}
            variables={variables}
            itemGroups={itemGroups}
            onUpdateWave={updateWave}
            onRemoveWave={(index) => update({
              waves: value.waves.filter((_, waveIndex) => waveIndex !== index),
            })}
          />
          <div className="analysis-inline-actions">
            <button
              type="button"
              className="secondary-button"
              disabled={value.waves.length >= 10}
              onClick={() => update({
                waves: [...value.waves, {
                  label: `T${value.waves.length + 1}`,
                  timeValue: value.waves.length,
                  xVariableId: null,
                  yVariableId: null,
                  xItemIds: [],
                  yItemIds: [],
                }],
              })}
            >
              添加波次
            </button>
            <label>
              <input
                type="checkbox"
                checked={value.constrainAcrossTime}
                onChange={(event) => update({ constrainAcrossTime: event.target.checked })}
              />
              约束相邻时间段路径相等
            </label>
            {value.measurementMode === 'latent_items' ? (
              <label>
                <input
                  type="checkbox"
                  checked={value.compareCompetingModels}
                  onChange={(event) => update({ compareCompetingModels: event.target.checked })}
                />
                同时拟合 CLPM 与 RI-CLPM 竞争模型
              </label>
            ) : null}
          </div>
          <PartialInvarianceFieldset
            value={value}
            positionCounts={positionCounts}
            onTogglePosition={togglePartialPosition}
          />
          {value.modelType === 'ri_clpm' && value.estimator !== 'WLSMV' ? (
            <LongitudinalPowerConfig
              value={value.powerAnalysis}
              onChange={(powerAnalysis) => update({ powerAnalysis })}
            />
          ) : null}
          <p className="method-note">
            潜变量模式会依次检验配置、载荷、截距/阈值与严格等值性，并使用通过实用拟合变化标准的最高层级。
            部分等值位置只能按理论事前指定；交叉滞后路径仍不能自动解释为因果效应。
          </p>
        </>
      ) : null}
    </div>
  )
}
