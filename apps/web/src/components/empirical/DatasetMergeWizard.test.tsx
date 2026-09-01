import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { DatasetMergeWizard } from './DatasetMergeWizard'
import type { DatasetVersion } from '../../types'

// Mock the API functions
vi.mock('../../api', () => ({
  importDataset: vi.fn(),
  mergeDatasets: vi.fn(),
}))

import { importDataset, mergeDatasets } from '../../api'

const mockPrimaryDataset: DatasetVersion = {
  schemaVersion: '1.0.0',
  id: 'ds_primary',
  projectId: 'default',
  createdAt: '2026-07-19T00:00:00Z',
  originalFile: {
    name: 'primary.csv',
    format: 'csv',
    sizeBytes: 1024,
    sha256: 'primary_hash',
  },
  storage: { raw: '', normalized: '' },
  rowCount: 10,
  columnCount: 2,
  variables: [
    {
      id: 'var_1',
      originalName: 'userId',
      label: 'User ID',
      storageType: 'int64',
      inferredType: 'id',
      confirmedType: 'id',
      confidence: 1,
      rationale: '',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 10,
      sampleValues: [1, 2, 3],
      valueLabels: {},
      issues: [],
    },
    {
      id: 'var_2',
      originalName: 'wave',
      label: 'Wave',
      storageType: 'int64',
      inferredType: 'ordinal',
      confirmedType: 'ordinal',
      confidence: 1,
      rationale: '',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 2,
      sampleValues: [1, 2],
      valueLabels: {},
      issues: [],
    },
  ],
  preview: [],
  warnings: [],
  dictionary: {
    version: 1,
    confirmedCount: 2,
    totalCount: 2,
    status: 'confirmed',
  },
}

const mockTargetDataset: DatasetVersion = {
  ...mockPrimaryDataset,
  id: 'ds_target',
  originalFile: {
    name: 'target.csv',
    format: 'csv',
    sizeBytes: 1024,
    sha256: 'target_hash',
  },
}

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

describe('DatasetMergeWizard', () => {
  it('renders upload step initially and navigates through configuration and merge report', async () => {
    const queryClient = createTestQueryClient()
    const handleMergeSuccess = vi.fn()
    const handleCancel = vi.fn()

    // Mock API implementations
    vi.mocked(importDataset).mockResolvedValue(mockTargetDataset)
    vi.mocked(mergeDatasets).mockResolvedValue({
      dataset: { ...mockPrimaryDataset, id: 'ds_merged', rowCount: 15 },
      report: {
        matchedCount: 8,
        primaryOnlyCount: 2,
        targetOnlyCount: 5,
        primaryDuplicates: 0,
        targetDuplicates: 0,
        warnings: [],
      },
    })

    render(
      <QueryClientProvider client={queryClient}>
        <DatasetMergeWizard
          primaryDataset={mockPrimaryDataset}
          onMergeSuccess={handleMergeSuccess}
          onCancel={handleCancel}
        />
      </QueryClientProvider>,
    )

    // Step 1: Upload step checks
    expect(screen.getByText('第一步：选择目标数据源')).toBeInTheDocument()
    const submitBtn = screen.getByText('下一步')
    expect(submitBtn).toBeDisabled()

    // Simulate selecting a file
    const file = new File(['dummy content'], 'target.csv', { type: 'text/csv' })
    const fileInput = screen.getByLabelText(/点击选择或拖拽文件到此处/i)
    fireEvent.change(fileInput, { target: { files: [file] } })

    expect(screen.getByText('target.csv')).toBeInTheDocument()
    expect(submitBtn).toBeEnabled()

    // Click next step
    fireEvent.click(submitBtn)

    // Wait for API call and step 2
    await waitFor(() => {
      expect(importDataset).toHaveBeenCalledWith(file)
      expect(screen.getByText('第二步：配置合并关联键')).toBeInTheDocument()
    })

    // Assert suggested keys
    const subjectSelect = screen.getByLabelText(/被试主键/i) as HTMLSelectElement
    expect(subjectSelect.value).toBe('userId')

    const executeBtn = screen.getByText('开始执行合并')
    expect(executeBtn).toBeEnabled()

    // Execute merge
    fireEvent.click(executeBtn)

    // Wait for step 3: Merge diagnostics
    await waitFor(() => {
      expect(mergeDatasets).toHaveBeenCalledWith('ds_primary', 'ds_target', 'userId', 'wave')
      expect(screen.getByText('第三步：合并诊断与结果确认')).toBeInTheDocument()
    })

    // Check diagnostics display
    expect(screen.getByText('8')).toBeInTheDocument() // matchedCount
    expect(screen.getByText('2')).toBeInTheDocument() // primaryOnlyCount
    expect(screen.getByText('5')).toBeInTheDocument() // targetOnlyCount

    // Click confirm
    const confirmBtn = screen.getByText('应用并确认新版本')
    fireEvent.click(confirmBtn)

    expect(handleMergeSuccess).toHaveBeenCalledWith(expect.objectContaining({
      id: 'ds_merged',
      rowCount: 15,
    }))
  })
})
