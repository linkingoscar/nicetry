import type React from 'react'

export interface DatasetVariableItem {
  id: string
  name: string
  label?: string
  type: 'numeric' | 'categorical' | 'datetime' | 'text'
  levels?: string[] | number
  missingRate?: number
  recommendedRoles?: string[]
}

export interface DatasetVariablePickerProps {
  label: string
  variables: DatasetVariableItem[]
  selectedIds: string[]
  onChange: (ids: string[]) => void
  isMulti?: boolean
  roleHint?: string
  placeholder?: string
}

export const DatasetVariablePicker: React.FC<DatasetVariablePickerProps> = ({
  label,
  variables,
  selectedIds,
  onChange,
  isMulti = false,
  roleHint,
  placeholder = '选择变量...',
}) => {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (isMulti) {
      const options = Array.from(e.target.selectedOptions).map(o => o.value)
      onChange(options)
    } else {
      onChange(e.target.value ? [e.target.value] : [])
    }
  }

  return (
    <div className="adv-variable-picker" style={{ marginBottom: '16px' }}>
      <label className="adv-picker-label" style={{ display: 'block', fontWeight: 600, marginBottom: '6px' }}>
        {label}
        {roleHint && <span className="muted" style={{ fontWeight: 400, marginLeft: '8px', fontSize: '0.85em' }}>({roleHint})</span>}
        <select
          className="adv-select"
          value={isMulti ? selectedIds : selectedIds[0] || ''}
          onChange={handleChange}
          multiple={isMulti}
          style={{ width: '100%', minHeight: isMulti ? '120px' : '38px', padding: '8px', marginTop: '4px' }}
        >
          {!isMulti && <option value="">{placeholder}</option>}
          {variables.map(v => (
            <option key={v.id} value={v.id}>
              {v.label ? `${v.label} (${v.name})` : v.name}
              {` — [${v.type}${v.missingRate !== undefined ? `, 缺失 ${(v.missingRate * 100).toFixed(1)}%` : ''}]`}
            </option>
          ))}
        </select>
      </label>
      {selectedIds.length > 0 && (
        <div className="adv-selected-tags" style={{ marginTop: '6px', display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
          {selectedIds.map(id => {
            const v = variables.find(item => item.id === id)
            return (
              <span key={id} className="adv-tag" style={{ background: '#e2e8f0', padding: '2px 8px', borderRadius: '4px', fontSize: '0.85em' }}>
                {v ? (v.label || v.name) : id}
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
