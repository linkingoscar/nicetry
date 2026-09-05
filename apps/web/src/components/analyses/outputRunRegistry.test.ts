import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../../types'
import {
  readRegisteredOutputRuns,
  registerOutputRun,
  registeredOutputFreshness,
} from './outputRunRegistry'

const indexMocks = vi.hoisted(() => ({
  registerServerAnalysisRun: vi.fn(),
}))

vi.mock('../../api/analysis-index', () => ({
  registerServerAnalysisRun: indexMocks.registerServerAnalysisRun,
}))

const dataset = {
  id: 'dataset_current',
  projectId: 'project_demo',
} as DatasetVersion

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
  indexMocks.registerServerAnalysisRun.mockResolvedValue({})
})

describe('outputRunRegistry', () => {
  it('stores model and advanced job references without inventing result state', () => {
    registerOutputRun({
      runId: 'run_model_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: 'measurement_1',
      source: 'model',
      label: '简单中介',
      methodId: 'model.process',
      modelId: 'model_demo',
      createdAt: '2026-09-03T10:00:00Z',
    })
    registerOutputRun({
      runId: 'run_advanced_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: null,
      source: 'advanced',
      label: '组间析因方差分析',
      methodId: 'experimental_design.factorial_anova.long.single_outcome',
      family: 'experimental_design',
      createdAt: '2026-09-03T11:00:00Z',
    })

    expect(readRegisteredOutputRuns(dataset.projectId)).toEqual([
      expect.objectContaining({ runId: 'run_advanced_1', source: 'advanced' }),
      expect.objectContaining({ runId: 'run_model_1', source: 'model' }),
    ])
    expect(JSON.stringify(readRegisteredOutputRuns(dataset.projectId))).not.toContain('succeeded')
    expect(indexMocks.registerServerAnalysisRun).toHaveBeenCalledTimes(2)
    expect(indexMocks.registerServerAnalysisRun).toHaveBeenCalledWith(
      dataset.projectId,
      expect.not.objectContaining({ result: expect.anything() }),
    )
  })

  it('deduplicates a run id and keeps the newest reference', () => {
    const base = {
      runId: 'run_same',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: null,
      source: 'advanced' as const,
      methodId: 'experimental_design.ancova.long.single_outcome',
      family: 'experimental_design',
    }
    registerOutputRun({ ...base, label: '旧名称', createdAt: '2026-09-03T10:00:00Z' })
    registerOutputRun({ ...base, label: 'ANCOVA', createdAt: '2026-09-03T12:00:00Z' })

    const runs = readRegisteredOutputRuns(dataset.projectId)
    expect(runs).toHaveLength(1)
    expect(runs[0]).toMatchObject({ label: 'ANCOVA', createdAt: '2026-09-03T12:00:00Z' })
  })

  it('assigns repeated runs of the same model to one stable analysis identity', () => {
    const base = {
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: 'measurement_1',
      source: 'model' as const,
      label: 'SEM',
      methodId: 'model.sem',
      modelId: 'model_same',
    }
    registerOutputRun({ ...base, runId: 'run_model_1', createdAt: '2026-09-03T10:00:00Z' })
    registerOutputRun({ ...base, runId: 'run_model_2', createdAt: '2026-09-03T11:00:00Z' })

    const runs = readRegisteredOutputRuns(dataset.projectId)
    expect(runs).toHaveLength(2)
    expect(runs[0].analysisId).toBe(runs[1].analysisId)
  })

  it('marks model runs stale when their dataset or measurement identity changes', () => {
    const current = {
      runId: 'run_1',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: 'measurement_1',
      source: 'model' as const,
      label: 'SEM',
      methodId: 'model.sem',
      createdAt: '2026-09-03T10:00:00Z',
    }
    expect(registeredOutputFreshness(current, dataset, { id: 'measurement_1' } as never)).toBe('current')
    expect(registeredOutputFreshness({ ...current, datasetVersionId: 'dataset_old' }, dataset, { id: 'measurement_1' } as never)).toBe('stale')
    expect(registeredOutputFreshness(current, dataset, { id: 'measurement_2' } as never)).toBe('stale')
  })

  it('does not make experiment or multilevel runs stale only because the measurement changed', () => {
    const advanced = {
      runId: 'run_anova',
      projectId: dataset.projectId,
      datasetVersionId: dataset.id,
      measurementVersionId: 'measurement_1',
      source: 'advanced' as const,
      label: 'ANOVA',
      methodId: 'experimental_design.factorial_anova.long.single_outcome',
      family: 'experimental_design',
      createdAt: '2026-09-03T10:00:00Z',
    }
    expect(registeredOutputFreshness(advanced, dataset, { id: 'measurement_2' } as never)).toBe('current')
    expect(registeredOutputFreshness({ ...advanced, family: 'questionnaire_measurement' }, dataset, { id: 'measurement_2' } as never)).toBe('stale')
  })
})
