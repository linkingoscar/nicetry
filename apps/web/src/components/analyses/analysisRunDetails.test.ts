import { beforeEach, describe, expect, it } from 'vitest'

import type { DatasetVersion, EmpiricalAnalysisJob } from '../../types'
import { readAnalysisRunDetails, syncEmpiricalAnalysisRunDetail } from './analysisRunDetails'

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

function job(id: string, status: EmpiricalAnalysisJob['status'], factorCount = 1): EmpiricalAnalysisJob {
  return {
    id,
    datasetId: dataset.id,
    modelId: 'empirical',
    modelVersion: 1,
    modelVersionId: 'empirical_v1',
    status,
    stage: status,
    progress: status === 'succeeded' ? 1 : 0,
    completedReplicates: 0,
    totalReplicates: 0,
    cancelRequested: false,
    createdAt: '2026-09-03T01:00:00Z',
    updatedAt: status === 'succeeded' ? '2026-09-03T01:02:00Z' : '2026-09-03T01:00:00Z',
    error: null,
    result: null,
    jobKind: 'empirical',
    measurementVersion: null,
    measurementVersionId: null,
    reportId: `report_${id}`,
    warnings: [],
    options: {
      procedure: 'descriptives',
      analysisVariableIds: ['score'],
      constructIds: [],
      factorCount,
      groupVariableId: null,
      aggregationVariableId: null,
      outcomeVariableId: null,
      predictorVariableIds: [],
      controlVariableIds: [],
    },
    metadata: null,
  }
}

function seedRun(id: string) {
  localStorage.setItem('researchpath.empirical.runs.v1:dataset_demo:null', JSON.stringify([
    { id, procedure: 'descriptives', createdAt: '2026-09-03T01:00:00Z' },
  ]))
}

beforeEach(() => {
  localStorage.clear()
})

describe('analysis run details', () => {
  it('updates one run in place while preserving its frozen draft revision', () => {
    seedRun('run_1')
    expect(syncEmpiricalAnalysisRunDetail(dataset, null, job('run_1', 'queued'))).toBe(true)
    expect(syncEmpiricalAnalysisRunDetail(dataset, null, job('run_1', 'succeeded'))).toBe(true)

    expect(readAnalysisRunDetails(dataset.projectId)).toEqual([
      expect.objectContaining({
        runId: 'run_1',
        draftRevision: 1,
        runStatus: 'succeeded',
        resultId: 'report_run_1',
        qualityStatus: 'clean',
      }),
    ])
  })

  it('reuses a revision for an identical submitted spec and increments after a spec change', () => {
    seedRun('run_1')
    syncEmpiricalAnalysisRunDetail(dataset, null, job('run_1', 'succeeded'))

    localStorage.setItem('researchpath.empirical.runs.v1:dataset_demo:null', JSON.stringify([
      { id: 'run_3', procedure: 'descriptives', createdAt: '2026-09-03T03:00:00Z' },
      { id: 'run_2', procedure: 'descriptives', createdAt: '2026-09-03T02:00:00Z' },
      { id: 'run_1', procedure: 'descriptives', createdAt: '2026-09-03T01:00:00Z' },
    ]))
    syncEmpiricalAnalysisRunDetail(dataset, null, { ...job('run_2', 'succeeded'), createdAt: '2026-09-03T02:00:00Z' })
    syncEmpiricalAnalysisRunDetail(dataset, null, { ...job('run_3', 'succeeded', 2), createdAt: '2026-09-03T03:00:00Z' })

    const byId = new Map(readAnalysisRunDetails(dataset.projectId).map((detail) => [detail.runId, detail]))
    expect(byId.get('run_1')?.draftRevision).toBe(1)
    expect(byId.get('run_2')?.draftRevision).toBe(1)
    expect(byId.get('run_3')?.draftRevision).toBe(2)
  })
})
