import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../types'
import { OutputWorkspace } from './OutputWorkspace'

vi.mock('./analyses/useOutputRunJobs', () => ({
  useOutputRunJobs: () => new Map(),
}))

const dataset: DatasetVersion = {
  schemaVersion: '1.0.0',
  id: 'dataset_demo',
  projectId: 'project_demo',
  createdAt: '2026-09-03T00:00:00Z',
  originalFile: {
    name: 'survey.csv',
    format: 'csv',
    sizeBytes: 128,
    sha256: 'a'.repeat(64),
  },
  storage: { raw: 'raw', normalized: 'normalized' },
  rowCount: 10,
  columnCount: 1,
  variables: [],
  preview: [],
  warnings: [],
  dictionary: {
    version: 1,
    confirmedCount: 0,
    totalCount: 0,
    status: 'draft',
  },
}

const legacyKey = 'researchpath.empirical.runs.v1:dataset_demo:null'

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem(legacyKey, JSON.stringify([
    {
      id: 'run_selected',
      procedure: 'descriptives',
      analysisId: 'analysis_selected',
      createdAt: '2026-09-03T01:00:00Z',
    },
  ]))
})

describe('OutputWorkspace run routing', () => {
  it('opens the exact selected current run instead of only the analysis draft', () => {
    const onOpenProcedure = vi.fn()
    render(
      <OutputWorkspace
        dataset={dataset}
        measurement={null}
        onOpenProcedure={onOpenProcedure}
      />,
    )

    fireEvent.click(screen.getByText('查看运行历史'))
    fireEvent.click(screen.getByRole('button', { name: /run_selected/ }))
    fireEvent.click(screen.getByRole('button', { name: '打开该运行结果 / 设置' }))

    expect(onOpenProcedure).toHaveBeenCalledWith('descriptives', 'analysis_selected', 'run_selected')
  })
})
