import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { DatasetVariable } from '../types'
import { VariableTable } from './VariableTable'

const variables: DatasetVariable[] = [
  {
    id: 'var_1',
    originalName: 'satisfaction',
    label: '满意度',
    storageType: 'int64',
    inferredType: 'ordinal',
    confirmedType: null,
    confidence: 0.82,
    rationale: '整数取值为 3–7 个有序等级，疑似 Likert/等级变量',
    missingCount: 0,
    missingRate: 0,
    uniqueCount: 5,
    sampleValues: [1, 2, 3, 4, 5],
    valueLabels: {},
    issues: [],
    minimum: 1,
    maximum: 5,
  },
]

describe('VariableTable', () => {
  it('treats the inferred type as usable until the user explicitly overrides it', () => {
    const onSave = vi.fn()
    render(<VariableTable variables={variables} isSaving={false} onSave={onSave} />)

    expect(screen.getByText('自动识别可用')).toBeInTheDocument()
    expect(screen.getByText(/1 个变量尚未人工确认/)).toBeInTheDocument()

    const select = screen.getByLabelText('满意度的有效类型')
    expect(select).toHaveValue('ordinal')
    fireEvent.change(select, { target: { value: 'likert' } })
    fireEvent.click(screen.getByRole('button', { name: '保存变量类型' }))

    expect(onSave).toHaveBeenCalledWith([
      { id: 'var_1', confirmedType: 'likert' },
    ])
  })
})
