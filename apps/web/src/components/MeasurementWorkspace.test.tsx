import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { saveMeasurement } from '../api'
import type { DatasetVariable } from '../types'
import { MeasurementWorkspace } from './MeasurementWorkspace'

vi.mock('../api', () => ({
  saveMeasurement: vi.fn(() => new Promise(() => undefined)),
}))

const variables: DatasetVariable[] = [1, 2, 3].map((number) => ({
  id: `var_${number}_abc0000${number}`,
  originalName: `q${number}`,
  label: `题项 ${number}`,
  storageType: 'int64',
  inferredType: 'ordinal',
  confirmedType: null,
  confidence: 0.82,
  rationale: 'Likert 题项',
  missingCount: 0,
  missingRate: 0,
  uniqueCount: 5,
  sampleValues: [1, 2, 3, 4, 5],
  valueLabels: {},
  issues: [],
  minimum: 1,
  maximum: 5,
}))

function renderWorkspace() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MeasurementWorkspace datasetId="dataset_1234567890abcdef" variables={variables} />
    </QueryClientProvider>,
  )
}

describe('MeasurementWorkspace', () => {
  beforeEach(() => {
    vi.mocked(saveMeasurement).mockClear()
  })

  it('uses inferred item types before global confirmation and submits the default 80% rule', async () => {
    renderWorkspace()
    fireEvent.change(screen.getByLabelText('构念 1 名称'), {
      target: { value: '工作投入' },
    })
    fireEvent.click(screen.getByRole('checkbox', { name: /题项 1q1/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: /题项 2q2/ }))
    fireEvent.click(screen.getByRole('checkbox', { name: '题项 2反向计分' }))
    fireEvent.click(screen.getByRole('button', { name: '保存规则并生成量表版本' }))

    await waitFor(() => expect(saveMeasurement).toHaveBeenCalledTimes(1))
    expect(saveMeasurement).toHaveBeenCalledWith(
      'dataset_1234567890abcdef',
      [expect.objectContaining({
        name: '工作投入',
        itemIds: ['var_1_abc00001', 'var_2_abc00002'],
        reverseItemIds: ['var_2_abc00002'],
        aggregation: 'mean',
        minimumValidProportion: 0.8,
        theoreticalMinimum: 1,
        theoreticalMaximum: 5,
      })],
      '',
    )
  })

  it('does not submit an incomplete construct', () => {
    renderWorkspace()
    fireEvent.click(screen.getByRole('button', { name: '保存规则并生成量表版本' }))

    expect(screen.getByRole('alert')).toHaveTextContent('至少两个题项')
    expect(saveMeasurement).not.toHaveBeenCalled()
  })
})
