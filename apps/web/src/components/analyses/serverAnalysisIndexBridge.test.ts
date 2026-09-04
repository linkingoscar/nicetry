import { describe, expect, it } from 'vitest'

import type { ServerAnalysisIndex } from '../../api/analysis-index'
import { mergeEmpiricalServerIndex, mergeRegisteredServerRuns } from './serverAnalysisIndexBridge'

const serverIndex: ServerAnalysisIndex = {
  schemaVersion: '1.0.0',
  projectId: 'default',
  rebuiltFromServerJobs: true,
  documents: [
    {
      id: 'analysis_server_empirical',
      projectId: 'default',
      title: '服务端描述统计',
      methodId: 'empirical.overview.descriptives',
      categoryId: 'descriptives-relations',
      source: 'empirical',
      datasetVersionId: 'dataset_demo',
      measurementVersionId: null,
      procedure: 'descriptives',
      createdAt: '2026-09-04T01:00:00Z',
      updatedAt: '2026-09-04T01:00:00Z',
      pinned: false,
    },
  ],
  runs: [
    {
      id: 'run_server_empirical',
      analysisId: 'analysis_server_empirical',
      projectId: 'default',
      source: 'empirical',
      methodId: 'empirical.overview.descriptives',
      label: '服务端描述统计',
      datasetVersionId: 'dataset_demo',
      measurementVersionId: null,
      status: 'succeeded',
      reportId: 'empirical_report_1',
      createdAt: '2026-09-04T01:02:00Z',
    },
    {
      id: 'run_server_model',
      analysisId: 'analysis_server_model',
      projectId: 'default',
      source: 'model',
      methodId: 'model.sem',
      label: '结构方程模型（SEM）',
      modelId: 'model_demo',
      datasetVersionId: 'dataset_demo',
      measurementVersionId: 'measurement_1',
      status: 'succeeded',
      createdAt: '2026-09-04T01:03:00Z',
    },
  ],
}

describe('serverAnalysisIndexBridge', () => {
  it('restores empirical documents and runs when the browser index is empty', () => {
    const merged = mergeEmpiricalServerIndex(
      { schemaVersion: '1.0.0', migrationVersion: 1, documents: [], runs: [] },
      serverIndex,
    )

    expect(merged.documents).toEqual([
      expect.objectContaining({
        id: 'analysis_server_empirical',
        title: '服务端描述统计',
        procedure: 'descriptives',
      }),
    ])
    expect(merged.runs).toEqual([
      expect.objectContaining({
        id: 'run_server_empirical',
        analysisId: 'analysis_server_empirical',
        resultId: 'empirical_report_1',
      }),
    ])
  })

  it('restores model and advanced run references without any statistical result payload', () => {
    const merged = mergeRegisteredServerRuns([], serverIndex)

    expect(merged).toEqual([
      expect.objectContaining({
        runId: 'run_server_model',
        source: 'model',
        methodId: 'model.sem',
        modelId: 'model_demo',
      }),
    ])
    expect(JSON.stringify(merged)).not.toContain('result')
  })

  it('does not overwrite newer local title and pin metadata with an older server response', () => {
    const merged = mergeEmpiricalServerIndex({
      schemaVersion: '1.0.0',
      migrationVersion: 1,
      documents: [{
        id: 'analysis_server_empirical',
        projectId: 'default',
        title: '刚刚重命名的分析',
        methodId: 'empirical.overview.descriptives',
        categoryId: 'descriptives-relations',
        createdAt: '2026-09-04T01:00:00Z',
        updatedAt: '2026-09-04T02:00:00Z',
        pinned: true,
        currentDraftId: 'draft_local',
        source: 'empirical',
        datasetVersionId: 'dataset_demo',
        measurementVersionId: null,
        procedure: 'descriptives',
      }],
      runs: [],
    }, serverIndex)

    expect(merged.documents[0]).toMatchObject({
      title: '刚刚重命名的分析',
      pinned: true,
      updatedAt: '2026-09-04T02:00:00Z',
    })
  })
})