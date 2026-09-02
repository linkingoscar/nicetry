import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../types'
import { DataWorkspaceDatasetBody } from './DataWorkspaceDatasetBody'

vi.mock('./VariableTable', () => ({
  VariableTable: () => <input aria-label="变量草稿" />,
}))
vi.mock('./MeasurementWorkspace', () => ({
  MeasurementWorkspace: () => <input aria-label="量表草稿" />,
}))
vi.mock('./DataQualityWorkspace', () => ({
  DataQualityWorkspace: () => <input aria-label="质量草稿" />,
}))
vi.mock('./DataStructureSetup', () => ({
  DataStructureSetup: () => <div>数据结构工具</div>,
}))
vi.mock('./context/StructureMeasurementPreparation', () => ({
  StructureMeasurementPreparation: () => <div>结构测量准备</div>,
}))
vi.mock('./data/DataGridView', () => ({
  DataGridView: () => <div>数据网格</div>,
}))
vi.mock('./empirical/DatasetMergeWizard', () => ({
  DatasetMergeWizard: () => <div>合并向导</div>,
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
  rowCount: 2,
  columnCount: 1,
  variables: [{
    id: 'score',
    originalName: 'score',
    label: '得分',
    storageType: 'float64',
    inferredType: 'continuous',
    confirmedType: null,
    confidence: 0.95,
    rationale: 'numeric',
    missingCount: 0,
    missingRate: 0,
    uniqueCount: 2,
    sampleValues: [1, 2],
    valueLabels: {},
    issues: [],
  }],
  preview: [{ score: 1 }, { score: 2 }],
  warnings: [],
  dictionary: {
    version: 1,
    confirmedCount: 0,
    totalCount: 1,
    status: 'draft',
  },
}

function renderBody() {
  const mutationStub = {
    isPending: false,
    reset: vi.fn(),
    mutate: vi.fn(),
  } as never

  render(
    <DataWorkspaceDatasetBody
      dataset={dataset}
      selectedFile={null}
      activeSheet=""
      importMutation={mutationStub}
      dictionaryMutation={mutationStub}
      structureKey=""
      structureReady
      analysisLabel="进入分析"
      onSheetChange={vi.fn()}
      showMergeWizard={false}
      onShowMergeWizardChange={vi.fn()}
      onMergedDatasetReset={vi.fn()}
      onMergeSuccess={vi.fn()}
      onDictionarySave={vi.fn()}
      onStructureValidityChange={vi.fn()}
      onContinueToAnalysis={vi.fn()}
    />,
  )
}

describe('DataWorkspaceDatasetBody', () => {
  it('keeps subview drafts mounted while switching tabs', async () => {
    const user = userEvent.setup()
    renderBody()

    expect(screen.getByRole('tab', { name: '数据视图' })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('数据网格')).toBeVisible()

    await user.click(screen.getByRole('tab', { name: '量表' }))
    const scaleDraft = screen.getByLabelText('量表草稿')
    await user.type(scaleDraft, '工作投入')

    await user.click(screen.getByRole('tab', { name: '变量视图' }))
    expect(scaleDraft).not.toBeVisible()

    await user.click(screen.getByRole('tab', { name: '量表' }))
    expect(screen.getByLabelText('量表草稿')).toHaveValue('工作投入')
  })

  it('preserves data-quality configuration when the tool is collapsed', async () => {
    const user = userEvent.setup()
    renderBody()

    const toggle = screen.getByRole('button', { name: '数据检查' })
    await user.click(toggle)
    const qualityDraft = screen.getByLabelText('质量草稿')
    await user.type(qualityDraft, '30')

    await user.click(toggle)
    expect(qualityDraft).not.toBeVisible()

    await user.click(toggle)
    expect(screen.getByLabelText('质量草稿')).toHaveValue('30')
  })
})
