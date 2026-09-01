import { describe, expect, it, vi } from 'vitest'

import type { DatasetVersion, MeasurementVersion } from '../types'
import { buildModelVariables, createCustomModelTemplate, createModelTemplate } from './model-builder/modelTemplates'
import { addVariableToCanvasModel, changeModelNodeRole, reconnectModelEdge } from './model-builder/modelCanvasActions'
import { activeRunStorageKey, restoreActiveRunId } from './model-builder/runPersistence'
import { addStructuralNodeModel, assignVariableToModel, removeModelEdges, removeStructuralNodeModel } from './model-builder/modelStructureActions'
import { createModelCanvasHandlers } from './model-builder/modelCanvasHandlers'
import { buildModelForEstimationFamily } from './model-builder/modelBuilderEstimation'


const dataset: DatasetVersion = {
  schemaVersion: '1.0.0',
  id: 'dataset_1234567890abcdef',
  projectId: 'default',
  createdAt: '2026-07-13T00:00:00Z',
  originalFile: {
    name: 'model.csv',
    format: 'csv',
    sizeBytes: 100,
    sha256: 'a'.repeat(64),
  },
  storage: { raw: 'raw.csv', normalized: 'data.parquet' },
  rowCount: 40,
  columnCount: 2,
  variables: [
    {
      id: 'var_1_12345678',
      originalName: 'age',
      label: '年龄',
      storageType: 'int64',
      inferredType: 'continuous',
      confirmedType: 'continuous',
      confidence: 0.9,
      rationale: '连续变量',
      missingCount: 0,
      missingRate: 0,
      uniqueCount: 40,
      sampleValues: [20, 21],
      valueLabels: {},
      issues: [],
    },
  ],
  preview: [],
  warnings: [],
  dictionary: { version: 1, confirmedCount: 1, totalCount: 1, status: 'confirmed' },
}

const scoreVariables = ['x', 'm', 'y', 'w'].map((role) => ({
  id: `scale_${role}`,
  label: role.toUpperCase(),
  type: 'scale_score' as const,
}))

const measurement: MeasurementVersion = {
  schemaVersion: '1.0.0',
  id: 'measurement_1234567890abcdef',
  datasetVersionId: dataset.id,
  version: 1,
  createdAt: '2026-07-13T00:00:00Z',
  changeNote: null,
  status: 'ready_for_model_canvas',
  constructs: [],
  reports: [],
  derivedDataset: {
    id: 'derived_1234567890abcdef',
    sourceDatasetVersionId: dataset.id,
    measurementVersion: 1,
    storage: 'derived.parquet',
    sha256: 'b'.repeat(64),
    rowCount: 40,
    columnCount: 5,
    scoreVariables,
  },
  transformationPreview: [],
  transformationLog: [],
  warnings: [],
}

describe('M3 model templates', () => {
  const variables = buildModelVariables(dataset, measurement)

  it('removes latent definitions and high-order references on delete or observed reassignment', () => {
    const model = createModelTemplate('model_4', variables, measurement)
    model.estimation.family = 'sem'
    model.nodes = model.nodes.map(node => ({ ...node, variableId: undefined, kind: 'latent' }))
    model.latents = model.nodes.map(node => ({ id: node.id, name: node.label, indicators: [`${node.id}_1`, `${node.id}_2`] }))
    model.latents.push({ id: 'higher', name: 'Higher', indicators: ['node_x', 'node_m', 'node_y'], level: 'higher_order' } as NonNullable<typeof model.latents>[number])
    const deleted = removeStructuralNodeModel(model, 'node_m')
    expect(deleted.latents?.map(latent => latent.id)).toEqual(['node_x', 'node_y', 'higher'])
    expect(deleted.latents?.at(-1)?.indicators).toEqual(['node_x', 'node_y'])
    const observed = variables.at(-1)
    if (!observed) throw new Error('Missing observed fixture')
    const assigned = assignVariableToModel(model, 'node_m', observed, variables)
    expect(assigned.nodes.find(node => node.id === 'node_m')?.kind).toBe('observed')
    expect(assigned.latents?.some(latent => latent.id === 'node_m')).toBe(false)
    // Original snapshot remains usable for undo and serialized draft recovery.
    expect(JSON.parse(JSON.stringify(model)).latents).toHaveLength(4)
    expect(buildModelForEstimationFamily(model, 'sem', variables, measurement)).toBe(model)
    const ols = createModelTemplate('model_4', variables, measurement)
    expect(buildModelForEstimationFamily(ols, 'ols', variables, measurement)).toBe(ols)
  })

  it.each([
    ['model_1', [['node_x', 'node_y']], 'edge_x_y'],
    ['model_4', [['node_x', 'node_m'], ['node_x', 'node_y'], ['node_m', 'node_y']], null],
    ['model_5', [['node_x', 'node_m'], ['node_x', 'node_y'], ['node_m', 'node_y']], 'edge_x_y'],
    ['model_7', [['node_x', 'node_m'], ['node_x', 'node_y'], ['node_m', 'node_y']], 'edge_x_m'],
    ['model_14', [['node_x', 'node_m'], ['node_x', 'node_y'], ['node_m', 'node_y']], 'edge_m_y'],
  ] as const)('creates canonical %s structure', (template, expectedEdges, moderationTarget) => {
    const model = createModelTemplate(template, variables, measurement)

    expect(model.edges.map((edge) => [edge.from, edge.to])).toEqual(expectedEdges)
    expect(model.moderations[0]?.targetEdgeId ?? null).toBe(moderationTarget)
    expect(model.datasetVersionId).toBe(measurement.derivedDataset.id)
    expect(new Set(model.nodes.map((node) => node.variableId)).size).toBe(model.nodes.length)
  })

  it.each([
    ['model_2', 2],
    ['model_3', 3],
  ] as const)('creates the two-moderator structure for %s', (template, moderationCount) => {
    const model = createModelTemplate(template, variables, measurement)

    expect(model.nodes.map((node) => node.role)).toEqual(['x', 'y', 'w', 'z'])
    expect(model.moderations).toHaveLength(moderationCount)
    expect(model.moderations.at(-1)).toMatchObject(
      template === 'model_3'
        ? {
            secondaryModeratorNodeId: 'node_z',
            moderatorProductTermId: 'term_w_z',
            productTermId: 'term_x_w_z',
          }
        : { moderatorNodeId: 'node_z', productTermId: 'term_x_z' },
    )
  })

  it.each([
    ['model_8', ['edge_x_m', 'edge_x_y']],
    ['model_15', ['edge_m_y', 'edge_x_y']],
    ['model_21', ['edge_x_m', 'edge_m_y']],
    ['model_22', ['edge_x_m', 'edge_m_y', 'edge_x_y']],
    ['model_58', ['edge_x_m', 'edge_m_y']],
    ['model_59', ['edge_x_m', 'edge_m_y', 'edge_x_y']],
  ] as const)('creates canonical multi-path moderation for %s', (template, targets) => {
    const model = createModelTemplate(template, variables, measurement)

    expect(model.moderations.map((item) => item.targetEdgeId)).toEqual(targets)
    if (template === 'model_21' || template === 'model_22') {
      expect(model.nodes.map((node) => node.role)).toEqual(['x', 'm', 'y', 'w', 'z'])
      expect(model.moderations[1].moderatorNodeId).toBe('node_z')
    }
  })

  it('places scale scores before observed variables in the model library', () => {
    expect(variables.slice(0, 4).every((variable) => variable.kind === 'scale_score')).toBe(true)
    expect(variables.at(-1)).toMatchObject({
      label: '年龄',
      kind: 'observed',
      encodingHint: { method: 'mean_center', label: '均值中心化' },
    })
  })

  it('starts custom construction with unbound slots and no assumed paths', () => {
    const model = createCustomModelTemplate(variables, measurement)

    expect(model.name).toBe('自定义 PROCESS 结构')
    expect(model.nodes.map((node) => node.role)).toEqual(['x', 'y'])
    expect(model.edges).toEqual([])
    expect(model.nodes.every(node => !node.variableId)).toBe(true)
    expect(model.moderations).toEqual([])
  })

  it('uses the explicitly chosen drop role without adding paths', () => {
    const custom = createCustomModelTemplate(variables, measurement)
    const mediator = variables.find((variable) => variable.id === 'scale_m')
    if (!mediator) throw new Error('测试变量缺少 M')

    const updated = addVariableToCanvasModel(custom, mediator, { x: 320, y: 120 }, 'w')

    expect(updated.nodes.map((node) => node.role)).toEqual(['x', 'y', 'w'])
    expect(updated.edges).toEqual([])
  })

  it('restores the active analysis run for the same dataset and model', () => {
    const key = activeRunStorageKey(dataset.id, 'model_example')
    localStorage.setItem(key, 'run_1234567890abcdef')

    expect(restoreActiveRunId(dataset.id, 'model_example')).toBe(
      'run_1234567890abcdef',
    )
    expect(restoreActiveRunId(dataset.id, 'different_model')).toBeNull()
  })

  it('changes roles without duplicate unique roles or dangling moderation/control references', () => {
    const original = createModelTemplate('model_59', variables, measurement)
    const changed = changeModelNodeRole(original, 'node_m', 'w')
    expect(changed.nodes.find(n => n.id === 'node_w')?.role).toBe('m')
    expect(changed.nodes.filter(n => n.role === 'w')).toHaveLength(1)
    expect(changed.edges.map(e => e.id)).toEqual(['edge_x_y'])
    expect(changed.moderations).toEqual([])
    expect(original.edges).toHaveLength(3)
    const reversed = reconnectModelEdge(original, 'edge_x_y', 'node_y', 'node_x')
    expect(reversed.edges.find(e => e.id === 'edge_x_y')).toMatchObject({ from: 'node_y', to: 'node_x', label: '' })
    expect(() => reconnectModelEdge(original, 'edge_x_y', 'node_x', 'node_m')).toThrow('已经存在')
    expect(() => reconnectModelEdge(original, 'edge_x_y', 'node_x', 'node_x')).toThrow('不能相同')
  })

  it('removes moderation references when their target path is deleted', () => {
    const model = createModelTemplate('model_59', variables, measurement)
    const updated = removeModelEdges(model, ['edge_x_m'])
    expect(updated.edges.map(edge => edge.id)).toEqual(['edge_x_y', 'edge_m_y'])
    expect(updated.moderations.map(item => item.targetEdgeId)).toEqual(['edge_m_y', 'edge_x_y'])
    expect(model.moderations).toHaveLength(3)
  })

  it('cleans control outcomes, moderation and centering after removing a mediator', () => {
    const model = createModelTemplate('model_59', variables, measurement)
    model.covariates = [{ nodeId: 'node_cov_age', outcomeNodeIds: ['node_m', 'node_y'] }]
    model.estimation.centering.nodeIds = ['node_m', 'node_x']
    const updated = removeStructuralNodeModel(model, 'node_m')
    expect(updated.edges.map(edge => edge.id)).toEqual(['edge_x_y'])
    expect(updated.moderations.map(item => item.targetEdgeId)).toEqual(['edge_x_y'])
    expect(updated.covariates[0].outcomeNodeIds).toEqual(['node_y'])
    expect(updated.estimation.centering.nodeIds).toEqual(['node_x'])
    expect(updated.canvas?.positions).not.toHaveProperty('node_m')
  })

  it('moves a bound variable to an empty role without duplicating its assignment', () => {
    const model = addStructuralNodeModel(createModelTemplate('model_4', variables, measurement), 'w')
    const variable = variables.find(item => item.id === model.nodes[0].variableId)
    if (!variable) throw new Error('测试变量缺少 X')
    const updated = assignVariableToModel(model, 'node_w', variable, variables)
    expect(updated.nodes.filter(node => node.variableId === variable.id)).toHaveLength(1)
    expect(updated.nodes.find(node => node.id === 'node_w')?.variableId).toBe(variable.id)
    expect(updated.nodes.find(node => node.id === 'node_x')?.variableId).toBeUndefined()
  })

  it('requires an explicit moderation target when multiple paths enter the same outcome', () => {
    const model = createModelTemplate('model_5', variables, measurement)
    model.moderations = []
    const update = vi.fn()
    const error = vi.fn()
    const handlers = createModelCanvasHandlers(variables, model, update, vi.fn(), error)
    handlers.handleConnect({ source: 'node_w', target: 'node_y', sourceHandle: null, targetHandle: null })
    expect(update).not.toHaveBeenCalled()
    expect(error).toHaveBeenCalledWith(expect.stringContaining('无法唯一确定'))
    handlers.handleConnect({ source: 'node_w', target: 'node_m', sourceHandle: null, targetHandle: null })
    expect(update).toHaveBeenCalledOnce()
    const next = update.mock.calls[0][0](model)
    expect(next.moderations).toEqual([expect.objectContaining({ targetEdgeId: 'edge_x_m', moderatorNodeId: 'node_w' })])
  })
})
