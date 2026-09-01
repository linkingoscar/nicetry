import type React from 'react'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

export interface ImputationWizardSpec {
  family: 'multiple_imputation'
  datasetVersionId?: string
  method: 'mice_fcs'
  imputations: number
  iterations: number
  variables: Array<{ variableId: string; method: 'auto' | 'pmm' | 'logreg' | 'polyreg' | 'polr' }>
  pooling: 'none' | 'rubin'
  diagnostics: Array<'trace' | 'distribution' | 'overimputation'>
  seed?: number
}

export interface ImputationWizardProps {
  spec: ImputationWizardSpec
  onChange: (spec: ImputationWizardSpec) => void
  variables: DatasetVariableItem[]
}

export const ImputationWizard: React.FC<ImputationWizardProps> = ({ spec, onChange, variables }) => {
  const update = (patch: Partial<ImputationWizardSpec>) => {
    onChange({ ...spec, ...patch })
  }

  const selectedVariableIds = (spec.variables || []).map(v => v.variableId)

  const handleSelectionChange = (ids: string[]) => {
    const updatedVars = ids.map(id => {
      const existing = spec.variables?.find(v => v.variableId === id)
      if (existing) return existing
      const meta = variables.find(v => v.id === id)
      let defaultMethod: 'auto' | 'pmm' | 'logreg' | 'polyreg' | 'polr' = 'pmm'
      if (meta?.type === 'categorical') {
        defaultMethod = meta.levels === 2 ? 'logreg' : 'polyreg'
      }
      return { variableId: id, method: defaultMethod }
    })
    update({ variables: updatedVars })
  }

  return (
    <div className="adv-imputation-wizard-panel" style={{ padding: '16px', border: '1px solid #cbd5e1', borderRadius: '8px' }}>
      <h3>多重插补与 Pooled 分析配置向导 (Multiple Imputation Wizard)</h3>
      <p className="muted">类型安全 MICE (PMM / Logistic / Polyreg / Polr)、插补数据集生成与 Rubin / Barnard-Rubin Pooling。</p>

      <div style={{ marginTop: '16px' }}>
        <DatasetVariablePicker
          label="待插补/模型变量 (Variables for Imputation)"
          variables={variables}
          selectedIds={selectedVariableIds}
          onChange={handleSelectionChange}
          isMulti={true}
          roleHint="选择包含缺失或用于预测的数据变量"
        />
      </div>

      {spec.variables && spec.variables.length > 0 && (
        <div style={{ marginTop: '16px' }}>
          <h4>变量特定插补类型映射 (Typed Methods)</h4>
          <table className="adv-table" style={{ width: '100%', marginTop: '8px', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f1f5f9', textAlign: 'left' }}>
                <th style={{ padding: '6px' }}>变量</th>
                <th style={{ padding: '6px' }}>类型</th>
                <th style={{ padding: '6px' }}>指定 MICE 插补方法</th>
              </tr>
            </thead>
            <tbody>
              {spec.variables.map((item, idx) => {
                const meta = variables.find(v => v.id === item.variableId)
                return (
                  <tr key={item.variableId} style={{ borderBottom: '1px solid #e2e8f0' }}>
                    <td style={{ padding: '6px' }}>{meta?.label || meta?.name || item.variableId}</td>
                    <td style={{ padding: '6px' }}><code>{meta?.type || 'numeric'}</code></td>
                    <td style={{ padding: '6px' }}>
                      <select
                        className="adv-select"
                        value={item.method}
                        onChange={e => {
                          const nextVars = [...spec.variables]
                          nextVars[idx] = { ...item, method: e.target.value as ImputationWizardSpec['variables'][0]['method'] }
                          update({ variables: nextVars })
                        }}
                        style={{ padding: '4px' }}
                      >
                        <option value="auto">auto (自动根据类型展开)</option>
                        <option value="pmm">pmm (Predictive Mean Matching - 连续)</option>
                        <option value="logreg">logreg (Logistic Regression - 二分类)</option>
                        <option value="polyreg">polyreg (Polytomous Regression - 多分类)</option>
                        <option value="polr">polr (Proportional Odds - 有序分类)</option>
                      </select>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginTop: '16px' }}>
        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            插补重数 ($m$)
            <input
              type="number"
              className="adv-input"
              value={spec.imputations ?? 20}
              onChange={e => update({ imputations: parseInt(e.target.value, 10) || 20 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            迭代轮次 (maxit)
            <input
              type="number"
              className="adv-input"
              value={spec.iterations ?? 20}
              onChange={e => update({ iterations: parseInt(e.target.value, 10) || 20 })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            />
          </label>
        </div>

        <div>
          <label style={{ fontWeight: 600, display: 'block', marginBottom: '4px' }}>
            下游 Pooled 汇合策略
            <select
              className="adv-select"
              value={spec.pooling || 'none'}
              onChange={e => update({ pooling: e.target.value as ImputationWizardSpec['pooling'] })}
              style={{ width: '100%', padding: '6px', marginTop: '4px' }}
            >
              <option value="none">none (仅生成插补数据集与诊断轨迹)</option>
              <option value="rubin">rubin (Rubin Pooling 线性/GLM 汇合推断)</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  )
}
