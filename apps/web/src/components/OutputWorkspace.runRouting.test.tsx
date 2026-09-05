import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion, EmpiricalAnalysisJob } from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { ensureEmpiricalAnalysisDocument } from './analyses/analysisDocuments'
import { OutputWorkspace } from './OutputWorkspace'

const indexMocks = vi.hoisted(() => ({
  getServerAnalysisIndex: vi.fn(),
  registerServerAnalysisRun: vi.fn(),
  upsertServerAnalysisDocument: vi.fn(),
  patchServerAnalysisDocument: vi.fn(),
}))
const outputMocks = vi.hoisted(() => ({
  useOutputRunJobs: vi.fn(),
  preview: vi.fn(),
}))

vi.mock('../api/analysis-index', () => indexMocks)
vi.mock('./analyses/useOutputRunJobs', () => ({
  useOutputRunJobs: outputMocks.useOutputRunJobs,
}))
vi.mock('./OutputEmpiricalRunPreview', () => ({
  OutputEmpiricalRunPreview: (props: unknown) => {
    outputMocks.preview(props)
    return <div>historical-empirical-preview</div>
  },
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

function renderOutput(onOpenProcedure: (
  procedure: EmpiricalProcedure,
  analysisId?: string,
  runId?: string,
  methodId?: string,
) => void) {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <OutputWorkspace dataset={dataset} measurement={null} onOpenProcedure={onOpenProcedure} />
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  outputMocks.useOutputRunJobs.mockReturnValue(new Map())
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

  it('restores and previews a historical run with the run own dataset and measurement versions', async () => {
    const historicalJob = {
      id: 'run_historical',
      jobKind: 'empirical',
      datasetId: 'dataset_old',
      measurementVersion: 3,
      measurementVersionId: 'measurement_old',
      reportId: 'report_historical',
      status: 'succeeded',
      options: {
        procedure: 'descriptives',
        analysisVariableIds: ['age'],
      },
    } as EmpiricalAnalysisJob
    outputMocks.useOutputRunJobs.mockReturnValue(new Map([['run_historical', historicalJob]]))
    indexMocks.getServerAnalysisIndex.mockResolvedValue({
      schemaVersion: '1.0.0',
      projectId: dataset.projectId,
      rebuiltFromServerJobs: true,
      documents: [{
        id: 'analysis_historical',
        projectId: dataset.projectId,
        title: '历史描述统计',
        methodId: 'empirical.overview.descriptives',
        categoryId: 'descriptives-relations',
        source: 'empirical',
        datasetVersionId: 'dataset_old',
        measurementVersionId: 'measurement_old',
        procedure: 'descriptives',
        createdAt: '2026-09-02T01:00:00Z',
        updatedAt: '2026-09-02T01:00:00Z',
        latestRunId: 'run_historical',
        pinned: false,
      }],
      runs: [{
        id: 'run_historical',
        analysisId: 'analysis_historical',
        projectId: dataset.projectId,
        source: 'empirical',
        methodId: 'empirical.overview.descriptives',
        label: '历史描述统计',
        datasetVersionId: 'dataset_old',
        measurementVersionId: 'measurement_old',
        status: 'succeeded',
        reportId: 'report_historical',
        createdAt: '2026-09-02T01:02:00Z',
      }],
    })

    renderOutput(vi.fn())

    expect(await screen.findByText('历史描述统计')).toBeInTheDocument()
    fireEvent.click(screen.getByText('查看运行历史'))
    fireEvent.click(screen.getByRole('button', { name: /run_historic/ }))
    expect(await screen.findByText('historical-empirical-preview')).toBeInTheDocument()
    expect(outputMocks.preview).toHaveBeenLastCalledWith(expect.objectContaining({
      datasetId: 'dataset_old',
      measurementVersion: 3,
      reportId: 'report_historical',
    }))
  })
})
