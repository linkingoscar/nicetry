import { useState } from 'react'

import type { DatasetVariable, VariableType } from '../types'
import { ScrollableResultTable } from './shared/ScrollableResultTable'

interface VariableTableProps {
  variables: DatasetVariable[]
  isSaving: boolean
  onSave: (updates: Array<{ id: string; confirmedType: VariableType }>) => void
}

const typeLabels: Record<VariableType, string> = {
  continuous: '连续变量',
  binary: '二分类',
  nominal: '无序分类',
  ordinal: '有序分类',
  likert: 'Likert 题项',
  id: '标识符',
  text: '文本',
}

const variableTypes = Object.keys(typeLabels) as VariableType[]

export function VariableTable({ variables, isSaving, onSave }: VariableTableProps) {
  const [confirmedTypes, setConfirmedTypes] = useState<Record<string, VariableType>>(() =>
    Object.fromEntries(
      variables.map((variable) => [
        variable.id,
        variable.confirmedType ?? variable.inferredType,
      ]),
    ),
  )

  const handleSave = () => {
    onSave(
      variables.map((variable) => ({
        id: variable.id,
        confirmedType: confirmedTypes[variable.id],
      })),
    )
  }

  return (
    <section className="dictionary-section" aria-labelledby="dictionary-heading">
      <div className="section-heading dictionary-heading-row">
        <div>
          <p className="eyebrow">数据字典</p>
          <h2 id="dictionary-heading">确认变量类型</h2>
        </div>
        <button className="secondary-button" type="button" onClick={handleSave} disabled={isSaving}>
          {isSaving ? '正在保存…' : '确认全部变量'}
        </button>
      </div>

      <ScrollableResultTable className="table-wrap" label="变量类型数据表，可横向滚动">
        <table className="variable-table">
          <thead>
            <tr>
              <th scope="col">变量</th>
              <th scope="col">数据概况</th>
              <th scope="col">系统建议</th>
              <th scope="col">最终类型</th>
              <th scope="col">状态</th>
            </tr>
          </thead>
          <tbody>
            {variables.map((variable) => (
              <tr key={variable.id}>
                <th scope="row">
                  <strong>{variable.label}</strong>
                  <code>{variable.originalName}</code>
                </th>
                <td>
                  <span>{variable.uniqueCount} 个唯一值</span>
                  {variable.missingRate > 0.05 ? (
                    <span className="health-chip is-alert">高缺失 {(variable.missingRate * 100).toFixed(1)}%</span>
                  ) : (
                    <small>缺失 {(variable.missingRate * 100).toFixed(1)}%</small>
                  )}
                  {variable.issues?.map((issue) => (
                    <span key={issue} className="health-chip is-warning">{issue}</span>
                  ))}
                </td>
                <td>
                  <strong>{typeLabels[variable.inferredType]}</strong>
                  <small>{variable.rationale}</small>
                </td>
                <td>
                  <label className="sr-only" htmlFor={`type-${variable.id}`}>
                    {variable.label}的最终类型
                  </label>
                  <select
                    id={`type-${variable.id}`}
                    value={confirmedTypes[variable.id]}
                    onChange={(event) =>
                      setConfirmedTypes((current) => ({
                        ...current,
                        [variable.id]: event.target.value as VariableType,
                      }))
                    }
                  >
                    {variableTypes.map((type) => (
                      <option key={type} value={type}>{typeLabels[type]}</option>
                    ))}
                  </select>
                </td>
                <td>
                  <span className={`dictionary-status ${variable.confirmedType ? 'is-confirmed' : ''}`}>
                    {variable.confirmedType ? '已确认' : '待确认'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollableResultTable>
    </section>
  )
}
