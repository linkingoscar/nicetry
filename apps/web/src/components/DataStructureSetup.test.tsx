import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { createDatasetStructureVersion, validateDatasetStructure } from '../api/studies'
import type { DatasetVariable, StudyContext } from '../types'
import { DataStructureSetup } from './DataStructureSetup'

vi.mock('../api/studies', () => ({
  createDatasetStructureVersion: vi.fn(),
  validateDatasetStructure: vi.fn(),
}))

const variables = ['person_id', 'wave', 'team_id'].map((id): DatasetVariable => ({
  id,
  originalName: id,
  label: id,
  inferredType: 'id',
  confirmedType: 'id',
  storageType: 'string',
  confidence: 1,
  rationale: 'test',
  missingCount: 0,
  missingRate: 0,
  uniqueCount: 10,
  sampleValues: [],
  valueLabels: {},
  issues: [],
}))
const context: StudyContext = {
  schemaVersion: '1.0.0',
  timeStructure: 'panel',
  dependenceStructure: 'nested',
  design: 'observational',
}

function renderSetupWith(
  setupVariables: DatasetVariable[],
  setupContext: StudyContext,
  onValidityChange = vi.fn(),
) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={client}>
      <DataStructureSetup
        datasetId="dataset_123"
        variables={setupVariables}
        context={setupContext}
        studyContextVersionId="context_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        initialStructure={null}
        onValidityChange={onValidityChange}
      />
    </QueryClientProvider>,
  )
  return onValidityChange
}

function renderSetup(onValidityChange = vi.fn()) {
  return renderSetupWith(variables, context, onValidityChange)
}

describe('DataStructureSetup', () => {
  beforeEach(() => {
    vi.mocked(validateDatasetStructure).mockReset()
    vi.mocked(createDatasetStructureVersion).mockReset()
  })

  it('requires distinct subject, time, and cluster roles before persisting', async () => {
    vi.mocked(validateDatasetStructure).mockResolvedValue({
      status: 'valid',
      proposedStructureHash: 'a'.repeat(64),
      profile: {
        rowCount: 10,
        missingRoleCounts: {},
        duplicateSubjectTimeCount: 0,
        subjectCount: 10,
        clusterCount: 2,
        singletonClusterCount: 0,
        clusterSize: { minimum: 5, median: 5, maximum: 5 },
        observationsPerSubject: { minimum: 1, median: 1, maximum: 1 },
        timePointCount: 1,
        nestingClassification: 'two_level',
      },
      warnings: [],
    })
    vi.mocked(createDatasetStructureVersion).mockResolvedValue({
      schemaVersion: '1.0.0',
      id: 'structure_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      projectId: 'default',
      datasetVersionId: 'dataset_123',
      revision: 1,
      studyContextVersionId: 'context_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      contextSnapshot: context,
      roles: { subjectId: 'person_id', timeId: 'wave', clusterId: 'team_id', groupId: null, treatmentId: null },
      profile: {
        rowCount: 10,
        missingRoleCounts: {},
        duplicateSubjectTimeCount: 0,
        subjectCount: 10,
        clusterCount: 2,
        singletonClusterCount: 0,
        clusterSize: { minimum: 5, median: 5, maximum: 5 },
        observationsPerSubject: { minimum: 1, median: 1, maximum: 1 },
        timePointCount: 1,
        nestingClassification: 'two_level',
      },
      status: 'valid',
      warnings: [],
      overrideReason: null,
      structureHash: 'b'.repeat(64),
      createdAt: '2026-08-01T00:00:00Z',
    })
    const validity = renderSetup()
    const selects = screen.getAllByRole('combobox')
    fireEvent.change(selects[0], { target: { value: 'person_id' } })
    fireEvent.change(selects[1], { target: { value: 'team_id' } })
    fireEvent.change(selects[2], { target: { value: 'wave' } })
    fireEvent.click(screen.getByRole('button', { name: '运行结构画像' }))

    await waitFor(() => expect(validateDatasetStructure).toHaveBeenCalledWith(
      'dataset_123',
      'context_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      expect.objectContaining({ subjectId: 'person_id', timeId: 'wave', clusterId: 'team_id' }),
    ))
    fireEvent.click(screen.getByRole('button', { name: '保存结构版本' }))
    await waitFor(() => expect(createDatasetStructureVersion).toHaveBeenCalledWith(
      'dataset_123',
      expect.objectContaining({ roles: expect.objectContaining({ subjectId: 'person_id', timeId: 'wave', clusterId: 'team_id' }) }),
    ))
    await waitFor(() => expect(validity).toHaveBeenLastCalledWith(true))
  })

  it('pre-fills subject and five-wave wide layout for the panel example', () => {
    const panelVariables = ['subject_id', 'age', 'x_t1_i1', 'x_t2_i1', 'x_t3_i1', 'x_t4_i1', 'x_t5_i1'].map((id): DatasetVariable => ({
      id,
      originalName: id,
      label: id,
      inferredType: id === 'subject_id' ? 'id' : 'continuous',
      confirmedType: id === 'subject_id' ? 'id' : 'continuous',
      storageType: id === 'subject_id' ? 'string' : 'float64',
      confidence: 1,
      rationale: 'test',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 10,
      sampleValues: [],
      valueLabels: {},
      issues: [],
    }))
    const panelContext: StudyContext = {
      schemaVersion: '1.0.0',
      timeStructure: 'panel',
      dependenceStructure: 'independent',
      design: 'observational',
    }

    renderSetupWith(panelVariables, panelContext)

    const selects = screen.getAllByRole('combobox')
    expect(selects[0]).toHaveValue('subject_id')
    expect(selects[1]).toHaveValue('wide')
    expect(screen.getByRole('spinbutton')).toHaveValue(5)
    expect(screen.getByText(/已按当前示例数据的字段和时间结构预填角色/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '运行结构画像' })).toBeEnabled()
  })

  it('pre-fills subject and day for the intensive longitudinal example', () => {
    const diaryVariables = ['person_id', 'day', 'daily_stress', 'scenario'].map((id): DatasetVariable => ({
      id,
      originalName: id,
      label: id,
      inferredType: id.endsWith('_id') ? 'id' : id === 'scenario' ? 'nominal' : 'continuous',
      confirmedType: id.endsWith('_id') ? 'id' : id === 'scenario' ? 'nominal' : 'continuous',
      storageType: id.endsWith('_id') || id === 'scenario' ? 'string' : 'float64',
      confidence: 1,
      rationale: 'test',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 10,
      sampleValues: [],
      valueLabels: {},
      issues: [],
    }))
    const diaryContext: StudyContext = {
      schemaVersion: '1.0.0',
      timeStructure: 'intensive_longitudinal',
      dependenceStructure: 'independent',
      design: 'observational',
    }

    renderSetupWith(diaryVariables, diaryContext)

    const selects = screen.getAllByRole('combobox')
    expect(selects[0]).toHaveValue('person_id')
    expect(selects[1]).toHaveValue('day')
    expect(screen.getByRole('button', { name: '运行结构画像' })).toBeEnabled()
  })
})
