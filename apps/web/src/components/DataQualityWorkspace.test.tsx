import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi } from 'vitest'

import { createAnalysisSample, runDataQuality } from '../api'
import type { DataQualityRun, DatasetVersion } from '../types'
import { DataQualityWorkspace } from './DataQualityWorkspace'

vi.mock('../api')

const dataset: DatasetVersion = {
  schemaVersion: '1.0.0',
  id: 'dataset_aaaaaaaaaaaaaaaa',
  projectId: 'default',
  createdAt: '2026-07-19T00:00:00Z',
  originalFile: { name: 'quality.csv', format: 'csv', sizeBytes: 10, sha256: 'a'.repeat(64) },
  storage: { raw: '', normalized: '' },
  rowCount: 2,
  columnCount: 4,
  variables: [
    { id: 'var_item_1', originalName: 'item_1', label: 'Item 1', storageType: 'int64', inferredType: 'ordinal', confirmedType: 'ordinal', confidence: 1, rationale: '', missingCount: 0, missingRate: 0, uniqueCount: 2, sampleValues: [1, 2], valueLabels: {}, issues: [] },
    { id: 'var_item_2', originalName: 'item_2', label: 'Item 2', storageType: 'int64', inferredType: 'ordinal', confirmedType: 'ordinal', confidence: 1, rationale: '', missingCount: 0, missingRate: 0, uniqueCount: 2, sampleValues: [1, 2], valueLabels: {}, issues: [] },
    { id: 'var_response_id', originalName: 'response_id', label: 'ResponseId', storageType: 'string', inferredType: 'id', confirmedType: 'id', confidence: 1, rationale: '', missingCount: 0, missingRate: 0, uniqueCount: 2, sampleValues: ['R1', 'R2'], valueLabels: {}, issues: [] },
    { id: 'var_duration', originalName: 'duration_seconds', label: 'Duration', storageType: 'int64', inferredType: 'continuous', confirmedType: 'continuous', confidence: 1, rationale: '', missingCount: 0, missingRate: 0, uniqueCount: 2, sampleValues: [30, 40], valueLabels: {}, issues: [] },
  ],
  preview: [],
  warnings: [],
  dictionary: { version: 1, confirmedCount: 4, totalCount: 4, status: 'confirmed' },
}

const qualityRun = {
  schemaVersion: '1.0.0',
  id: 'quality_aaaaaaaaaaaaaaaa',
  datasetVersionId: dataset.id,
  datasetSha256: 'a'.repeat(64),
  createdAt: '2026-07-19T00:00:00Z',
  request: { qualityVariableIds: ['var_item_1'], attentionChecks: [] },
  rowCount: 2,
  caseMetricsPath: 'quality/cases.parquet',
  caseMetricsHash: 'b'.repeat(64),
  detectedRoles: {},
  metrics: { duration: { median: 35 }, duplicateResponseId: { duplicateRowCount: 0 }, attentionChecks: { failedRowCount: 0 } },
} as DataQualityRun

describe('DataQualityWorkspace', () => {
  it('runs quality checks and creates an analysis sample version', async () => {
    vi.mocked(runDataQuality).mockResolvedValue(qualityRun)
    vi.mocked(createAnalysisSample).mockResolvedValue({
      id: 'sample_aaaaaaaaaaaaaaaa',
      schemaVersion: '1.0.0',
      datasetVersionId: dataset.id,
      datasetSha256: 'a'.repeat(64),
      qualityRunId: qualityRun.id,
      createdAt: '2026-07-19T00:00:00Z',
      label: '主分析样本',
      combineOperator: 'or',
      rules: [],
      rowCount: 2,
      includedCount: 2,
      excludedCount: 0,
      boundaryCount: 0,
      sampleHash: 'c'.repeat(64),
      caseRecordsPath: 'sample/cases.parquet',
      caseRecordsHash: 'd'.repeat(64),
    })
    const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
    render(<QueryClientProvider client={queryClient}><DataQualityWorkspace dataset={dataset} /></QueryClientProvider>)

    fireEvent.click(screen.getByText('运行案例级质量检查'))
    await waitFor(() => expect(screen.getByText(`质量运行 ${qualityRun.id}`)).toBeInTheDocument())
    expect(screen.getByText('指标已生成')).toBeInTheDocument()
    expect(screen.getByText(/质量运行只生成审计指标和标记，不生成未经预注册的单一总分/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('生成主分析样本版本'))
    await waitFor(() => expect(screen.getByText(/已生成 sample_/)).toBeInTheDocument())
    expect(createAnalysisSample).toHaveBeenCalled()
  })

  it('does not display longitudinal or quality values before a real run exists', () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
    render(<QueryClientProvider client={queryClient}><DataQualityWorkspace dataset={dataset} /></QueryClientProvider>)

    expect(screen.queryByText('纵向留存率')).not.toBeInTheDocument()
    expect(screen.queryByText('重测 ICC')).not.toBeInTheDocument()
    expect(screen.getByText('尚未运行质量检查')).toBeInTheDocument()
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
  })
})
