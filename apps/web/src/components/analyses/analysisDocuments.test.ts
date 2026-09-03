import { beforeEach, describe, expect, it } from 'vitest'

import type { DatasetVersion } from '../../types'
import {
  analysisDocumentsForDataset,
  analysisRunsForDocument,
  loadEmpiricalAnalysisIndex,
} from './analysisDocuments'

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
})

describe('analysis document compatibility index', () => {
  it('groups repeated procedure runs under one stable analysis document', () => {
    localStorage.setItem(legacyKey, JSON.stringify([
      { id: 'run_desc_2', procedure: 'descriptives', createdAt: '2026-09-03T02:00:00Z' },
      { id: 'run_corr_1', procedure: 'correlation', createdAt: '2026-09-03T01:30:00Z' },
      { id: 'run_desc_1', procedure: 'descriptives', createdAt: '2026-09-03T01:00:00Z' },
    ]))

    const index = loadEmpiricalAnalysisIndex(dataset, null)
    const documents = analysisDocumentsForDataset(index, dataset, null)

    expect(documents).toHaveLength(2)
    expect(index.runs).toHaveLength(3)

    const descriptives = documents.find((document) => document.procedure === 'descriptives')
    expect(descriptives).toMatchObject({
      title: '描述统计',
      methodId: 'empirical.overview.descriptives',
      latestRunId: 'run_desc_2',
      datasetVersionId: dataset.id,
      measurementVersionId: null,
    })
    expect(analysisRunsForDocument(index, descriptives?.id ?? '').map((run) => run.id)).toEqual([
      'run_desc_2',
      'run_desc_1',
    ])
  })

  it('is idempotent and keeps the legacy recovery index intact', () => {
    localStorage.setItem(legacyKey, JSON.stringify([
      { id: 'run_freq_1', procedure: 'frequencies', createdAt: '2026-09-03T01:00:00Z' },
    ]))

    const first = loadEmpiricalAnalysisIndex(dataset, null)
    const second = loadEmpiricalAnalysisIndex(dataset, null)

    expect(first.documents).toHaveLength(1)
    expect(second.documents).toHaveLength(1)
    expect(second.runs).toHaveLength(1)
    expect(second.runs[0]).toMatchObject({
      id: 'run_freq_1',
      submittedSpec: null,
      runStatus: 'legacy_indexed',
      draftRevision: 0,
    })
    expect(localStorage.getItem(legacyKey)).toContain('run_freq_1')
  })
})
