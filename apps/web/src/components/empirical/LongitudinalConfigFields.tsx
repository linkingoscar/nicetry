import type { LongitudinalPanelOptions } from '../../types'
import type { Candidate } from './LongitudinalPanelConfig.types'
import {
  lockedLongitudinalModelType,
  useEmpiricalMethodSliceId,
} from './EmpiricalMethodScopeContext'

interface LongitudinalConfigFieldsProps {
  value: LongitudinalPanelOptions
  subjectCandidates: Candidate[]
  defaultSubjectId?: string | null
  onChange: (value: LongitudinalPanelOptions) => void
  update: (patch: Partial<LongitudinalPanelOptions>) => void
}

const MODEL_LABELS: Record<LongitudinalPanelOptions['modelType'], string> = {
  clpm: '传统 CLPM',
  ri_clpm: 'RI-CLPM',
  lcm_sr: 'LCM-SR',
}

export function LongitudinalConfigFields({
  value,
  subjectCandidates,
  defaultSubjectId,
  onChange,
  update,
}: LongitudinalConfigFieldsProps) {
  const methodSliceId = useEmpiricalMethodSliceId()
  const lockedModelType = lockedLongitudinalModelType(methodSliceId)

  return (
    <div className="empirical-config-grid">
      <label>测量模式
        <select
          value={value.measurementMode}
          onChange={(event) => {
            const measurementMode = event.target.value as LongitudinalPanelOptions['measurementMode']
            onChange({
              ...value,
              measurementMode,
              estimator: 'MLR',
              missing: 'fiml',
              waves: value.waves.map((wave) => ({
                ...wave,
                xVariableId: null,
                yVariableId: null,
                xItemIds: [],
                yItemIds: [],
              })),
              partialInvariancePositions: [],
              cmbSensitivity: measurementMode === 'latent_items'
                ? value.cmbSensitivity
                : 'none',
            })
          }}
        >
          <option value="observed_scores" disabled={value.modelType === 'lcm_sr'}>
            观测量表得分
          </option>
          <option value="latent_items">题项级潜变量</option>
        </select>
      </label>
      {lockedModelType ? (
        <div className="method-note" role="status">
          <strong>模型：{MODEL_LABELS[lockedModelType]}</strong>
          <span>由方法库选择锁定；如需切换模型，请返回“分析方法”选择另一方法。</span>
        </div>
      ) : (
        <label>模型
          <select
            value={value.modelType}
            onChange={(event) => {
              const modelType = event.target.value as LongitudinalPanelOptions['modelType']
              const minimumWaves = modelType === 'lcm_sr' ? 5 : modelType === 'ri_clpm' ? 3 : 2
              const waves = [...value.waves]
              while (waves.length < minimumWaves) {
                waves.push({
                  label: `T${waves.length + 1}`,
                  timeValue: waves.length,
                  xVariableId: null,
                  yVariableId: null,
                  xItemIds: [],
                  yItemIds: [],
                })
              }
              onChange({
                ...value,
                modelType,
                waves,
                measurementMode: modelType === 'lcm_sr' ? 'latent_items' : value.measurementMode,
                growthShape: modelType === 'lcm_sr' ? value.growthShape : 'linear',
                powerAnalysis: modelType === 'ri_clpm' ? value.powerAnalysis : null,
              })
            }}
          >
            <option value="ri_clpm">RI-CLPM（推荐，至少三时点）</option>
            <option value="clpm">传统 CLPM（至少两时点）</option>
            <option value="lcm_sr">LCM-SR（至少五时点）</option>
          </select>
        </label>
      )}
      {value.modelType === 'lcm_sr' ? (
        <label>宏观生长轨迹
          <select
            value={value.growthShape}
            onChange={(event) => update({
              growthShape:
                event.target.value as LongitudinalPanelOptions['growthShape'],
            })}
          >
            <option value="linear">线性生长</option>
            <option value="quadratic">线性 + 二次生长</option>
          </select>
        </label>
      ) : null}
      <label>被试 ID
        <select
          value={value.subjectVariableId}
          disabled={Boolean(defaultSubjectId)}
          onChange={(event) => update({ subjectVariableId: event.target.value })}
        >
          <option value="">请选择唯一被试标识</option>
          {subjectCandidates.map((candidate) => (
            <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
          ))}
        </select>
      </label>
      <label>估计方法
        <select
          value={value.estimator}
          onChange={(event) => update({
            estimator: event.target.value as LongitudinalPanelOptions['estimator'],
          })}
        >
          {value.indicatorScale === 'ordinal' ? (
            <option value="WLSMV">WLSMV 有序题项估计</option>
          ) : (
            <>
              <option value="MLR">MLR 稳健极大似然</option>
              <option value="ML">ML 极大似然</option>
            </>
          )}
        </select>
      </label>
      <label>缺失处理
        <select
          value={value.missing}
          onChange={(event) => update({
            missing: event.target.value as LongitudinalPanelOptions['missing'],
          })}
        >
          {value.estimator !== 'WLSMV' ? <option value="fiml">FIML</option> : null}
          <option value="complete_cases">完整案例</option>
        </select>
      </label>
      {value.measurementMode === 'latent_items' ? (
        <>
          <label>题项尺度
            <select
              value={value.indicatorScale}
              onChange={(event) => {
                const indicatorScale = event.target.value as LongitudinalPanelOptions['indicatorScale']
                update({
                  indicatorScale,
                  estimator: indicatorScale === 'ordinal' ? 'WLSMV' : 'MLR',
                  missing: indicatorScale === 'ordinal' ? 'complete_cases' : 'fiml',
                  powerAnalysis: indicatorScale === 'ordinal'
                    ? null
                    : value.powerAnalysis,
                  cmbSensitivity: indicatorScale === 'ordinal'
                    ? 'none'
                    : value.cmbSensitivity,
                })
              }}
            >
              <option value="continuous">连续近似</option>
              <option value="ordinal">有序分类</option>
            </select>
          </label>
          <label>最高等值性层级
            <select
              value={value.invarianceLevel}
              onChange={(event) => update({
                invarianceLevel: event.target.value as LongitudinalPanelOptions['invarianceLevel'],
              })}
            >
              <option value="configural">配置等值</option>
              <option value="metric">载荷等值</option>
              <option value="scalar">截距/阈值等值</option>
              <option value="strict">严格等值</option>
            </select>
          </label>
        </>
      ) : null}
      <label>
        <input
          type="checkbox"
          checked={value.runRobustnessChecks}
          onChange={(event) => update({ runRobustnessChecks: event.target.checked })}
        />
        自动运行路径约束与缺失策略稳健性检查
      </label>
      {value.measurementMode === 'latent_items' && value.indicatorScale === 'continuous' ? (
        <label>
          <input
            type="checkbox"
            checked={value.cmbSensitivity === 'global_ulmc'}
            onChange={(event) => update({
              cmbSensitivity: event.target.checked ? 'global_ulmc' : 'none',
              invarianceLevel: event.target.checked
                && !['scalar', 'strict'].includes(value.invarianceLevel)
                ? 'scalar'
                : value.invarianceLevel,
            })}
          />
          运行纵向全局正交方法因子（ULMC）敏感性分析
        </label>
      ) : null}
    </div>
  )
}
