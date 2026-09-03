import { beforeEach, describe, expect, it } from 'vitest'

import type { DatasetVersion } from '../../types'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import {
  empiricalDraftKey,
  migrateEmpiricalDraftToAnalysis,
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
  correlationPAdjust: 'BH',
  groupOmnibusPAdjust: 'holm',
  multiplicityPAdjust: 'BH',
  factorCount: 1,
  confidenceLevel: 0.95,
} as EmpiricalConfigValue

beforeEach(() => localStorage.clear())

describe('analysis-scoped empirical drafts', () => {
  it('migrates a legacy procedure draft without deleting the recovery key', () => {
    const legacyKey = empiricalDraftKey(dataset, null)
    const analysisKey = empiricalDraftKey(dataset, null, undefined, 'analysis_desc')
    const draft = { config, activeRunId: 'run_1', lastRunConfig: config }
    expect(saveEmpiricalDraft(legacyKey, draft)).toBe(true)

    expect(migrateEmpiricalDraftToAnalysis(dataset, null, undefined, 'analysis_desc', 'descriptives')).toEqual(draft)
    expect(readEmpiricalDraft(analysisKey, 'descriptives')).toEqual(draft)
    expect(readEmpiricalDraft(legacyKey, 'descriptives')).toEqual(draft)
  })

  it('keeps drafts for two analysis ids independent even when the procedure matches', () => {
    const firstKey = empiricalDraftKey(dataset, null, undefined, 'analysis_a')
    const secondKey = empiricalDraftKey(dataset, null, undefined, 'analysis_b')
    const first = { config, activeRunId: 'run_a', lastRunConfig: config }
    const secondConfig = { ...config, analysisVariableIds: ['age'] }
    const second = { config: secondConfig, activeRunId: 'run_b', lastRunConfig: secondConfig }

    saveEmpiricalDraft(firstKey, first)
    saveEmpiricalDraft(secondKey, second)

    expect(readEmpiricalDraft(firstKey, 'descriptives')?.activeRunId).toBe('run_a')
    expect(readEmpiricalDraft(secondKey, 'descriptives')?.activeRunId).toBe('run_b')
    expect(readEmpiricalDraft(firstKey, 'descriptives')?.config.analysisVariableIds).toEqual(['score'])
    expect(readEmpiricalDraft(secondKey, 'descriptives')?.config.analysisVariableIds).toEqual(['age'])
  })
})
