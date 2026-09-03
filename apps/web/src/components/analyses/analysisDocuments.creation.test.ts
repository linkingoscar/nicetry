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
  originalFile: { name: 'survey.csv', format: 'csv', sizeBytes: 10, sha256: 'a'.repeat(64) },
  storage: { raw: 'raw', normalized: 'normalized' },
  rowCount: 10,
  columnCount: 1,
  variables: [],
  preview: [],
  warnings: [],
  dictionary: { version: 1, confirmedCount: 0, totalCount: 0, status: 'draft' },
}

beforeEach(() => localStorage.clear())

describe('createEmpiricalAnalysisDocument', () => {
  it('allows two independent analysis documents to use the same method', () => {
    const first = createEmpiricalAnalysisDocument(dataset, null, 'correlation', '核心变量相关 A')
    const second = createEmpiricalAnalysisDocument(dataset, null, 'correlation', '核心变量相关 B')
    const index = loadEmpiricalAnalysisIndex(dataset, null)
    const documents = analysisDocumentsForDataset(index, dataset, null)

    expect(first.id).not.toBe(second.id)
    expect(documents.filter((document) => document.procedure === 'correlation')).toHaveLength(2)
    expect(documents.map((document) => document.title)).toEqual(expect.arrayContaining(['核心变量相关 A', '核心变量相关 B']))
    expect(index.runs).toHaveLength(0)
  })
})
