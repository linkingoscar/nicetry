import { describe, expect, it } from 'vitest'

import type { MeasurementVersion, ModelVariable } from '../../types'
import { buildBasicSemModel } from './semQuickForm'

const variables: ModelVariable[] = [
  {
    id: 'score_x',
    label: 'Predictor',
    kind: 'observed',
    dataType: 'continuous',
    source: 'score_x',
    encodingHint: { method: 'as_is', label: '原值', reason: 'test' },
  },
  {
    id: 'score_y',
    label: 'Outcome',
    kind: 'observed',
    dataType: 'continuous',
    source: 'score_y',
    encodingHint: { method: 'as_is', label: '原值', reason: 'test' },
  },
]

const measurement = {
  id: 'measurement_demo',
  datasetVersionId: 'dataset_demo',
  version: 1,
  constructs: [
    { id: 'cx', name: 'Predictor', outputVariableId: 'score_x', itemIds: ['x1', 'x2', 'x3'] },
    { id: 'cy', name: 'Outcome', outputVariableId: 'score_y', itemIds: ['y1', 'y2', 'y3'] },
  ],
  derivedDataset: {
    id: 'derived_demo',
    sourceDatasetVersionId: 'dataset_demo',
    measurementVersion: 1,
    storage: 'derived',
    sha256: 'a'.repeat(64),
    rowCount: 100,
    columnCount: 2,
    scoreVariables: [
      { id: 'score_x', label: 'Predictor', type: 'scale_score' },
      { id: 'score_y', label: 'Outcome', type: 'scale_score' },
    ],
  },
} as unknown as MeasurementVersion

describe('buildBasicSemModel', () => {
  it('builds a two-latent X→Y SEM from the current measurement version', () => {
    const model = buildBasicSemModel({
      predictorVariableId: 'score_x',
      outcomeVariableId: 'score_y',
      estimator: 'ML',
      confidenceLevel: 0.95,
      missing: 'fiml',
    }, variables, measurement)

    expect(model.estimation).toMatchObject({
      family: 'sem',
      estimator: 'ML',
      missing: 'fiml',
      confidenceLevel: 0.95,
    })
    expect(model.edges).toEqual([
      expect.objectContaining({ from: 'node_x', to: 'node_y', kind: 'regression' }),
    ])
    expect(model.nodes.find((node) => node.id === 'node_x')).toMatchObject({ kind: 'latent', variableId: undefined })
    expect(model.nodes.find((node) => node.id === 'node_y')).toMatchObject({ kind: 'latent', variableId: undefined })
    expect(model.latents).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'node_x', indicators: ['x1', 'x2', 'x3'] }),
      expect.objectContaining({ id: 'node_y', indicators: ['y1', 'y2', 'y3'] }),
    ]))
  })

  it('forces complete-case handling for WLSMV', () => {
    const model = buildBasicSemModel({
      predictorVariableId: 'score_x',
      outcomeVariableId: 'score_y',
      estimator: 'WLSMV',
      confidenceLevel: 0.99,
      missing: 'fiml',
    }, variables, measurement)

    expect(model.estimation.estimator).toBe('WLSMV')
    expect(model.estimation.missing).toBe('complete_cases_per_model')
  })

  it('rejects using the same construct on both sides of the structural path', () => {
    expect(() => buildBasicSemModel({
      predictorVariableId: 'score_x',
      outcomeVariableId: 'score_x',
      estimator: 'ML',
      confidenceLevel: 0.95,
      missing: 'fiml',
    }, variables, measurement)).toThrow(/必须不同/)
  })
})
