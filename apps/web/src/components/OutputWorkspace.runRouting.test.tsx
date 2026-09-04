import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../types'
import { ensureEmpiricalAnalysisDocument } from './analyses/analysisDocuments'
import { OutputWorkspace } from './OutputWorkspace'

const indexMocks = vi.hoisted(() => ({
  getServerAnalysisIndex: vi.fn(),
  registerServerAnalysisRun: vi.fn(),
  upsertServerAnalysisDocument: vi.fn(),
  patchServerAnalysisDocument: vi.fn(),
}))

vi.mock('../api/analysis-index', () => indexMocks)
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

function renderOutput(onOpenProcedure: ReturnType<typeof vi.fn>) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <OutputWorkspace dataset={dataset} measurement={null} onOpenProcedure={onOpenProcedure} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  indexMocks.getServerAnalysisIndex.mockResolvedValue({
    schemaVersion: '1.0.0',
    projectId: dataset.projectId,
    documents: [],
    runs: [],
    rebuiltFromServerJobs: true,
  })
  indexMocks.upsertServerAnalysisDocument.mockResolvedValue({})
})

describe('OutputWorkspace run routing', () => {
  it('opens the exact selected current run and preserves the stored method identity', () => {
    localStorage.setItem(legacyKey, JSON.stringify([
      {
        id: 'run_selected',
        procedure: 'descriptives',
        analysisId: 'analysis_selected',
        createdAt: '2026-09-03T01:00:00Z',
      },
    ]))
    const onOpenProcedure = vi.fn()
    renderOutput(onOpenProcedure)

    fireEvent.click(screen.getByText('查看运行历史'))
    fireEvent.click(screen.getByRole('button', { name: /run_selected/ }))
    fireEvent.click(screen.getByRole('button', { name: '打开该运行结果 / 设置' }))

    expect(onOpenProcedure).toHaveBeenCalledWith(
      'descriptives',
      'analysis_selected',
      'run_selected',
      'empirical.overview.descriptives',
    )
  })

  it('keeps a longitudinal method-scoped analysis locked when reopening a selected run', () => {
    const document = ensureEmpiricalAnalysisDocument(
      dataset,
      null,
      'longitudinal',
      'longitudinal.ri-clpm',
    )
    localStorage.setItem(legacyKey, JSON.stringify([
      {
        id: 'run_ri_clpm',
        procedure: 'longitudinal',
        analysisId: document.id,
        createdAt: '2026-09-03T02:00:00Z',
      },
    ]))

    const onOpenProcedure = vi.fn()
    renderOutput(onOpenProcedure)

    fireEvent.click(screen.getByText('查看运行历史'))
    fireEvent.click(screen.getByRole('button', { name: /run_ri_clpm/ }))
    fireEvent.click(screen.getByRole('button', { name: '打开该运行结果 / 设置' }))

    expect(onOpenProcedure).toHaveBeenCalledWith(
      'longitudinal',
      document.id,
      'run_ri_clpm',
      'longitudinal.ri-clpm',
    )
  })
})