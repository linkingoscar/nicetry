import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DatasetVersion } from '../../types'
import { DataGridView } from './DataGridView'

const dataset: DatasetVersion = {
  schemaVersion: '1.0',
  id: 'dataset-1',
  projectId: 'default',
  createdAt: '2026-09-03T00:00:00Z',
  originalFile: {
    name: 'survey.sav',
    format: 'sav',
    sizeBytes: 1024,
    sha256: 'abc123',
  },
  storage: { raw: 'raw', normalized: 'normalized' },
  rowCount: 2,
  columnCount: 2,
  variables: [
    {
      id: 'age',
      originalName: 'age',
      label: '年龄',
      storageType: 'numeric',
      inferredType: 'continuous',
      confirmedType: null,
      confidence: 0.98,
      rationale: 'numeric range',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 2,
      sampleValues: [29, 35],
      valueLabels: {},
      issues: [],
    },
    {
      id: 'engage1',
      originalName: 'engage1',
      label: '工作投入题项1',
      storageType: 'numeric',
      inferredType: 'likert',
      confirmedType: null,
      confidence: 0.96,
      rationale: 'five categories',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 2,
      sampleValues: [4, 5],
      valueLabels: {},
      issues: [],
    },
  ],
  preview: [
    { age: 29, engage1: 4 },
    { age: 35, engage1: 5 },
  ],
  warnings: [],
  dictionary: {
    version: 1,
    confirmedCount: 0,
    totalCount: 2,
    status: 'draft',
  },
}

describe('DataGridView', () => {
  it('renders a read-only dataset preview using inferred effective types', () => {
    render(<DataGridView dataset={dataset} />)

    expect(screen.getByRole('heading', { name: '当前数据' })).toBeInTheDocument()
    expect(screen.getByText('预览 2 / 2 个案例 · 2 个变量')).toBeInTheDocument()
    expect(screen.getByText('年龄')).toBeInTheDocument()
    expect(screen.getByText('工作投入题项1')).toBeInTheDocument()
    expect(screen.getByText('连续')).toBeInTheDocument()
    expect(screen.getByText('Likert')).toBeInTheDocument()
    expect(screen.getByText('29')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })
})
