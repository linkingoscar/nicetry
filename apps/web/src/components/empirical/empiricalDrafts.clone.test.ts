import { beforeEach, describe, expect, it } from 'vitest'

import type { DatasetVersion } from '../../types'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import {
  cloneEmpiricalDraftToAnalysis,
  empiricalDraftKey,
  readEmpiricalDraft,
  saveEmpiricalDraft,
} from './empiricalDrafts'

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

const config = {
  procedure: 'descriptives',
  analysisVariableIds: ['score'],
  constructIds: [],
  predictorVariableIds: [],
  controlVariableIds: [],
  responseSurfacePredictorIds: [],
  groupVariableId: null,
  aggregationVariableId: null,
  outcomeVariableId: null,
  correlationMethod: 'pearson',
  correlationPAdjust: 'BH',
  groupOmnibusPAdjust: 'holm',
  multiplicityPAdjust: 'BH',
  factorCount: 1,
  confidenceLevel: 0.95,
  multiplicityFamilyId: 'cross_sectional_inference',
  rotation: 'varimax',
  factorCountMethod: 'kaiser',
  parallelIterations: 1000,
  randomSeed: 20260714,
  sampleVersionId: null,
  longitudinalPanel: null,
  diaryMultilevel: null,
} satisfies EmpiricalConfigValue

beforeEach(() => localStorage.clear())

describe('cloneEmpiricalDraftToAnalysis', () => {
  it('copies configuration but not the source run identity', () => {
    const sourceKey = empiricalDraftKey(dataset, null, undefined, 'analysis_source')
    const targetKey = empiricalDraftKey(dataset, null, undefined, 'analysis_copy')
    saveEmpiricalDraft(sourceKey, { config, activeRunId: 'run_source', lastRunConfig: config, tabRequestKey: 7 })

    const cloned = cloneEmpiricalDraftToAnalysis(
      dataset,
      null,
      undefined,
      'analysis_source',
      'analysis_copy',
      'descriptives',
    )

    expect(cloned).toEqual({ config, activeRunId: null, lastRunConfig: null })
    expect(readEmpiricalDraft(targetKey, 'descriptives')).toEqual({ config, activeRunId: null, lastRunConfig: null })
    expect(readEmpiricalDraft(sourceKey, 'descriptives')?.activeRunId).toBe('run_source')
  })
})
