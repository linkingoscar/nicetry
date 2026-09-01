import { describe, expect, it } from 'vitest'
import type { ModelSpec, ResultBundle } from '../../types'
import { buildModelEdges, buildRenderedNodes } from '../modelCanvasGraph'
import { buildSemMeasurementGraph } from './semCanvasGraph'
import { buildPathEvidence } from './pathEvidence'
import { removeStructuralNodeModel } from './modelStructureActions'

const model = {
  nodes: [{ id: 'factor_a', label: 'A', role: 'x', kind: 'latent', dataType: 'continuous' },
    { id: 'outcome', variableId: 'raw_y', label: 'Y', role: 'y', kind: 'observed', dataType: 'continuous' }],
  edges: [{ id: 'a_y', from: 'factor_a', to: 'outcome', kind: 'regression' }],
  covariates: [], moderations: [],
  latents: ['a', 'b', 'c'].map(id => ({ id: `factor_${id}`, name: id, level: 'first_order', indicators: [`${id}_1`, `${id}_2`, `${id}_3`] })).concat([
    { id: 'higher', name: 'G', level: 'higher_order', indicators: ['factor_a', 'factor_b', 'factor_c'] },
  ]),
  estimation: { family: 'sem', centering: { nodeIds: [] } },
} as unknown as ModelSpec

describe('SEM measurement graph', () => {
  const base = buildRenderedNodes(model, {}, 'compact', new Map(), undefined, undefined)
  it.each([{ targets: ['factor_a'] }, { targets: ['outcome'] }, { targets: ['factor_a', 'outcome'] }, { targets: [] }])('draws exactly the explicit control targets $targets', ({ targets }) => {
    const controlled = { ...model, covariates: [{ nodeId: 'age', outcomeNodeIds: targets }] }
    const edges = buildModelEdges(controlled, {}, 'idle', 'all')
    expect(edges.filter(edge => edge.source === 'age').map(edge => edge.target)).toEqual(targets)
  })
  it('shows every measurement relation including nonstructural and higher-order factors', () => {
    const graph = buildSemMeasurementGraph(model, base, {}, { view: 'full', collapsed: [], labels: {} })
    expect(graph.nodes).toHaveLength(14)
    expect(graph.edges).toHaveLength(12)
    expect(graph.edges.find(edge => edge.id === 'loading:higher:factor_b')).toMatchObject({ source: 'higher', target: 'factor_b' })
    expect(graph.nodes.find(node => node.id === 'outcome')).toBeDefined()
    expect(graph.nodes.find(node => node.id === 'outcome')?.position.x).toBeGreaterThan(900)
    const measurement = buildSemMeasurementGraph(model, base, {}, { view: 'measurement', collapsed: [], labels: {} })
    expect(measurement.nodes.some(node => node.id === 'outcome')).toBe(false)
  })
  it('collapses presentation without altering model definitions and restores deleted factor snapshots', () => {
    const graph = buildSemMeasurementGraph(model, base, {}, { view: 'measurement', collapsed: ['factor_b'], labels: {} })
    expect(graph.nodes.some(node => node.id === 'indicator:b_1')).toBe(false)
    expect(model.latents?.find(latent => latent.id === 'factor_b')?.indicators).toHaveLength(3)
    const removed = removeStructuralNodeModel(model, 'factor_b')
    expect(removed.latents?.find(latent => latent.id === 'higher')?.indicators).toEqual(['factor_a', 'factor_c'])
    expect(buildSemMeasurementGraph(JSON.parse(JSON.stringify(model)), base, {}, { view: 'structure', collapsed: [], labels: {} }).nodes.map(node => node.id)).toEqual(['factor_a', 'outcome'])
  })
  it('maps raw loading and observed structural result identities without mixing standardized scales', () => {
    const result = { equations: [], semResult: {
      loadings: [{ latentId: 'factor_b', indicatorId: 'b_1', estimate: 2, stdAll: 0.7, standardError: 0.1, pValue: 0.01, ciLower: 1.8, ciUpper: 2.2 }],
      paths: [{ from: 'factor_a', to: 'raw_y', estimate: 3, stdAll: 0.5, standardError: 0.2, pValue: 0.01 }],
    } } as unknown as ResultBundle
    const evidence = buildPathEvidence(model, result, false)
    expect(evidence['loading:factor_b:b_1']).toMatchObject({ estimate: 2, lower: 1.8, upper: 2.2 })
    expect(evidence.a_y.estimate).toBe(3)
  })
})
