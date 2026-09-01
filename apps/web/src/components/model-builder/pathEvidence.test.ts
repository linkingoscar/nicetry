import { describe, expect, it } from 'vitest'

import type { ModelSpec, ResultBundle } from '../../types'
import { buildPathEvidence } from './pathEvidence'

const model = {
  edges: [
    { id: 'edge_x_m', from: 'node_x', to: 'node_m', kind: 'regression', label: 'a' },
    { id: 'edge_m_y', from: 'node_m', to: 'node_y', kind: 'regression', label: 'b' },
  ],
  moderations: [{ id: 'moderation_x_m', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_x_m' }],
} as ModelSpec

const result = {
  equations: [
    {
      formula: 'node_m ~ node_x + node_w + term_interaction_x_m',
      coefficients: [
        { term: 'node_x', estimate: 0.42, pValue: 0.01, confidenceInterval: { lower: 0.1, upper: 0.7 } },
        { term: 'term_interaction_x_m', estimate: 0.18, pValue: 0.03, confidenceInterval: { lower: 0.02, upper: 0.34 } },
      ],
    },
    {
      formula: 'node_y ~ node_m',
      coefficients: [
        { term: 'node_m', estimate: 0.05, pValue: 0.61, confidenceInterval: { lower: -0.14, upper: 0.24 } },
      ],
    },
  ],
} as ResultBundle

describe('path evidence mapping', () => {
  it('maps coefficient inference back to each visual edge', () => {
    const evidence = buildPathEvidence(model, result, false)
    expect(evidence.edge_x_m).toMatchObject({ estimate: 0.42, pValue: 0.01, status: 'inference_signal' })
    expect(evidence.edge_m_y).toMatchObject({ estimate: 0.05, pValue: 0.61, status: 'inference_uncertain' })
    expect(evidence['moderation:moderation_x_m']).toMatchObject({ estimate: 0.18, status: 'inference_signal' })
  })

  it('uses the reported interval before the p-value and never labels a path as theoretically supported', () => {
    const intervalResult = {
      ...result,
      equations: [{
        formula: 'node_m ~ node_x',
        coefficients: [{
          term: 'node_x',
          estimate: 0.2,
          pValue: 0.01,
          confidenceInterval: { lower: -0.01, upper: 0.41 },
        }],
      }],
    } as ResultBundle

    const evidence = buildPathEvidence(model, intervalResult, false)
    expect(evidence.edge_x_m.status).toBe('inference_uncertain')
    expect(Object.values(evidence).map((item) => item.status)).not.toContain('supported')
    expect(Object.values(evidence).map((item) => item.status)).not.toContain('unsupported')
  })

  it('marks every estimable relationship as running while the job is active', () => {
    const evidence = buildPathEvidence(model, undefined, true)
    expect(evidence.edge_x_m.status).toBe('running')
    expect(evidence['moderation:moderation_x_m'].status).toBe('running')
  })

  it('keeps SEM B, standard errors and intervals on the same unstandardized scale', () => {
    const semResult = { ...result, semResult: { paths: [{
      from: 'node_x', to: 'node_m', estimate: 1.8, stdAll: 0.4,
      standardError: 0.6, statistic: 3, pValue: 0.01, ciLower: -0.1, ciUpper: 3.7,
    }] } } as ResultBundle
    expect(buildPathEvidence(model, semResult, false).edge_x_m).toMatchObject({
      estimate: 1.8, standardError: 0.6, lower: -0.1, upper: 3.7, status: 'inference_uncertain',
    })
  })
})
