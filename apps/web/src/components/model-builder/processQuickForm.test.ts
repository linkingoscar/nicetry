import { describe, expect, it } from 'vitest'

import type { MeasurementVersion, ModelVariable } from '../../types'
import { buildProcessQuickModel } from './processQuickForm'

const variables: ModelVariable[] = ['x', 'm', 'w', 'y'].map((id) => ({
  id,
  label: id.toUpperCase(),
  kind: 'observed',
  dataType: 'continuous',
  source: id,
  encodingHint: { method: 'as_is', label: '原值', reason: 'test' },
}))

const measurement = {
  id: 'measurement_demo',
  datasetVersionId: 'dataset_demo',
  version: 1,
  constructs: [],
  derivedDataset: {
    id: 'derived_demo',
    sourceDatasetVersionId: 'dataset_demo',
    measurementVersion: 1,
    storage: 'derived',
    sha256: 'a'.repeat(64),
    rowCount: 100,
    columnCount: 4,
    scoreVariables: [],
  },
} as unknown as MeasurementVersion

describe('buildProcessQuickModel', () => {
  it('builds a Model 4 draft with explicit X/M/Y assignments and bootstrap settings', () => {
    const model = buildProcessQuickModel({
      kind: 'mediation',
      xVariableId: 'x',
      mediatorVariableId: 'm',
      yVariableId: 'y',
      confidenceLevel: 0.95,
      bootstrapReplicates: 8000,
      meanCenterPredictors: false,
    }, variables, measurement)

    expect(model.nodes.find((node) => node.role === 'x')?.variableId).toBe('x')
    expect(model.nodes.find((node) => node.role === 'm')?.variableId).toBe('m')
    expect(model.nodes.find((node) => node.role === 'y')?.variableId).toBe('y')
    expect(model.estimation.bootstrap).toMatchObject({ enabled: true, replicates: 8000 })
    expect(model.estimation.confidenceLevel).toBe(0.95)
    expect(model.estimation.centering).toEqual({ method: 'none', nodeIds: [] })
  })

  it('builds a Model 1 draft and mean-centers X/W when requested', () => {
    const model = buildProcessQuickModel({
      kind: 'moderation',
      xVariableId: 'x',
      moderatorVariableId: 'w',
      yVariableId: 'y',
      confidenceLevel: 0.99,
      bootstrapReplicates: 5000,
      meanCenterPredictors: true,
    }, variables, measurement)

    expect(model.nodes.find((node) => node.role === 'x')?.variableId).toBe('x')
    expect(model.nodes.find((node) => node.role === 'w')?.variableId).toBe('w')
    expect(model.nodes.find((node) => node.role === 'y')?.variableId).toBe('y')
    expect(model.moderations.length).toBeGreaterThan(0)
    expect(model.estimation.centering.method).toBe('mean')
    expect(model.estimation.centering.nodeIds.sort()).toEqual(
      model.nodes.filter((node) => node.role === 'x' || node.role === 'w').map((node) => node.id).sort(),
    )
  })

  it('rejects overlapping role assignments before creating a runnable draft', () => {
    expect(() => buildProcessQuickModel({
      kind: 'mediation',
      xVariableId: 'x',
      mediatorVariableId: 'x',
      yVariableId: 'y',
      confidenceLevel: 0.95,
      bootstrapReplicates: 5000,
      meanCenterPredictors: false,
    }, variables, measurement)).toThrow(/必须使用不同变量/)
  })
})
