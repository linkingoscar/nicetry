import type React from 'react'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

export interface LongitudinalWizardSpec {
  family: 'longitudinal_model'
  datasetVersionId?: string
  modelType: 'growth_curve' | 'clpm' | 'ri_clpm' | 'esm_diary'
  subjectId: string
  waves: Array<{ wave: string; timeValue: number; variables: Record<string, string> }>
  estimator: 'MLR' | 'ML' | 'WLSMV'
  missing: 'available_rows_ml' | 'fiml'
  groupVariableId?: string
}

export interface LongitudinalWizardProps {
  spec: LongitudinalWizardSpec
  onChange: (spec: LongitudinalWizardSpec) => void
  variables: DatasetVariableItem[]
}

export const LongitudinalWizard: React.FC<LongitudinalWizardProps> = ({ spec, onChange, variables }) => {
  const update = (patch: Partial<LongitudinalWizardSpec>) => {
    onChange({ ...spec, ...patch })
  }

  return (
    <div className="adv-longitudinal-wizard-panel" style={{ padding: '16px', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
      <h3>纵向与多层分析配置向导 (Longitudinal Model Wizard)</h3>
      <p className="muted">Observed Growth 观测增长曲线、CLPM/RI-CLPM 交叉滞后模型与 ESM 日记 AR(1) 分析。</p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            纵向模型架构 (Model Type)
            <select
              className="adv-select"
              value={spec.modelType || 'growth_curve'}
              onChange={e => update({ modelType: e.target.value as LongitudinalWizardSpec['modelType'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="growth_curve">潜增长 / 观测增长曲线 (Growth Curve)</option>
              <option value="ri_clpm">RI-CLPM 随机截距交叉滞后模型 (Between/Within 分解)</option>
              <option value="clpm">传统 CLPM 交叉滞后模型 (Observed Path)</option>
              <option value="esm_diary">ESM 经验取样 / 日记研究 AR(1) 模型</option>
            </select>
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            缺失数据机制 (Missing Handling)
            <select
              className="adv-select"
              value={spec.missing || 'available_rows_ml'}
              onChange={e => update({ missing: e.target.value as LongitudinalWizardSpec['missing'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="available_rows_ml">available_rows_ml (LMM 似然法利用可用行)</option>
              <option value="fiml">fiml (Lavaan 全信息极大似然法)</option>
            </select>
          </label>
        </div>
      </div>

      <div style={{ marginTop: '16px' }}>
        <DatasetVariablePicker
          label="个体 / 被试标识符 (Subject / Person ID)"
          variables={variables}
          selectedIds={spec.subjectId ? [spec.subjectId] : []}
          onChange={ids => update({ subjectId: ids[0] || '' })}
          isMulti={false}
          roleHint="用于跨时间波次追踪同一个体"
        />
      </div>

      <div style={{ marginTop: '16px' }}>
        <h4>波次映射与真实时间间隔 (Wave Time-Value Mapping)</h4>
        <table className="adv-table" style={{ width: '100%', marginTop: '8px', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
              <th style={{ padding: '6px' }}>波次标签</th>
              <th style={{ padding: '6px' }}>真实时间数值 (timeValue)</th>
              <th style={{ padding: '6px' }}>说明</th>
            </tr>
          </thead>
          <tbody>
            {(spec.waves || []).map((w, idx) => (
              <tr key={w.wave} style={{ borderBottom: '1px solid #e2e8f0' }}>
                <td style={{ padding: '6px' }}><code>{w.wave}</code></td>
                <td style={{ padding: '6px' }}>
                  <input
                    type="number"
                    step="0.5"
                    className="adv-input"
                    value={w.timeValue}
                    onChange={e => {
                      const nextWaves = [...spec.waves]
                      nextWaves[idx] = { ...w, timeValue: parseFloat(e.target.value) || 0 }
                      update({ waves: nextWaves })
                    }}
                    style={{ width: '100px', padding: '4px' }}
                  />
                </td>
                <td style={{ padding: '6px', color: '#64748b' }}>真实时间间隔度量（非机械 0,1,2）</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
