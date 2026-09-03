import { beforeEach, describe, expect, it } from 'vitest'

import type { DatasetVersion } from '../../types'
import {
  analysisDocumentsForDataset,
  createEmpiricalAnalysisDocument,
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

beforeEach(() => localStorage.clear())

describe('analysis document duplication primitives', () => {
  it('creates independent same-procedure analysis objects without copying runs', () => {
    const first = createEmpiricalAnalysisDocument(dataset, null, 'descriptives', '描述统计 A')
    const second = createEmpiricalAnalysisDocument(dataset, null, 'descriptives', '描述统计 B')
    const index = loadEmpiricalAnalysisIndex(dataset, null)
    const documents = analysisDocumentsForDataset(index, dataset, null)
      .filter((document) => document.procedure === 'descriptives')

    expect(first.id).not.toBe(second.id)
    expect(first.currentDraftId).not.toBe(second.currentDraftId)
    expect(documents.map((document) => document.title).sort()).toEqual(['描述统计 A', '描述统计 B'])
    expect(index.runs).toHaveLength(0)
    expect(first.latestRunId).toBeUndefined()
    expect(second.latestRunId).toBeUndefined()
  })
})
