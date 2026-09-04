import { describe, expect, it } from 'vitest'

import type { MeasurementVersion, ModelVariable } from '../../types'
import { buildProcessQuickModel, processQuickKindForRequest } from './processQuickForm'

const variables: ModelVariable[] = ['x', 'm', 'm2', 'w', 'y'].map((id) => ({
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
    columnCount: 5,
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

  it('builds parallel Model 4 and serial Model 6 drafts with two explicit mediators', () => {
    const parallel = buildProcessQuickModel({
      kind: 'parallel_mediation',
      xVariableId: 'x',
      mediatorVariableId: 'm',
      secondMediatorVariableId: 'm2',
      yVariableId: 'y',
      confidenceLevel: 0.95,
      bootstrapReplicates: 5000,
      meanCenterPredictors: false,
    }, variables, measurement)
    const serial = buildProcessQuickModel({
      kind: 'serial_mediation',
      xVariableId: 'x',
      mediatorVariableId: 'm',
      secondMediatorVariableId: 'm2',
      yVariableId: 'y',
      confidenceLevel: 0.95,
      bootstrapReplicates: 5000,
      meanCenterPredictors: false,
    }, variables, measurement)

    expect(parallel.name).toContain('Model 4')
    expect(parallel.nodes.filter((node) => node.role === 'm').map((node) => node.variableId)).toEqual(['m', 'm2'])
    expect(serial.name).toContain('Model 6')
    expect(serial.nodes.filter((node) => node.role === 'm').map((node) => node.variableId)).toEqual(['m', 'm2'])
    expect(serial.edges.some((edge) => edge.from === 'node_m1' && edge.to === 'node_m2')).toBe(true)
  })

  it('builds Model 7 with X/W centering on the moderated X→M path', () => {
    const model = buildProcessQuickModel({
      kind: 'moderated_mediation_first',
      xVariableId: 'x',
      mediatorVariableId: 'm',
      moderatorVariableId: 'w',
      yVariableId: 'y',
      confidenceLevel: 0.99,
      bootstrapReplicates: 5000,
      meanCenterPredictors: true,
    }, variables, measurement)

    expect(model.name).toContain('Model 7')
    expect(model.moderations.some((moderation) => moderation.targetEdgeId === 'edge_x_m')).toBe(true)
    expect(model.estimation.centering.nodeIds.sort()).toEqual(['node_w', 'node_x'])
  })

  it('builds Model 14 with M/W centering on the moderated M→Y path', () => {
    const model = buildProcessQuickModel({
      kind: 'moderated_mediation_second',
      xVariableId: 'x',
      mediatorVariableId: 'm',
      moderatorVariableId: 'w',
      yVariableId: 'y',
      confidenceLevel: 0.99,
      bootstrapReplicates: 5000,
      meanCenterPredictors: true,
    }, variables, measurement)

    expect(model.name).toContain('Model 14')
    expect(model.moderations.some((moderation) => moderation.targetEdgeId === 'edge_m_y')).toBe(true)
    expect(model.estimation.centering.nodeIds.sort()).toEqual(['node_m', 'node_w'])
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
    expect(model.estimation.centering.nodeIds.sort()).toEqual(['node_w', 'node_x'])
  })

  it('maps method-library model identity to the matching form kind', () => {
    expect(processQuickKindForRequest(4, 1)).toBe('mediation')
    expect(processQuickKindForRequest(4, 2)).toBe('parallel_mediation')
    expect(processQuickKindForRequest(6, 2)).toBe('serial_mediation')
    expect(processQuickKindForRequest(7, 1)).toBe('moderated_mediation_first')
    expect(processQuickKindForRequest(14, 1)).toBe('moderated_mediation_second')
    expect(processQuickKindForRequest()).toBeNull()
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
