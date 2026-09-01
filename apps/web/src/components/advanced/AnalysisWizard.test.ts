import { describe, expect, it } from 'vitest'

import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { buildAnalysisSpecTemplate } from './AnalysisWizard'
import type { DatasetVariableItem } from './DatasetVariablePicker'

const variables: DatasetVariableItem[] = [
  { id: 'y', name: 'y', label: '结果', type: 'numeric' },
  { id: 'x', name: 'x', label: '预测', type: 'numeric' },
  { id: 'age', name: 'age', label: '协变量', type: 'numeric' },
  { id: 'group', name: 'group', label: '组别', type: 'categorical' },
  { id: 'subject', name: 'subject', label: '被试', type: 'text' },
  { id: 'cluster', name: 'cluster', label: '聚类', type: 'categorical' },
]

const context = {
  dataset: { id: 'dataset_demo', hash: 'a'.repeat(64), sha256: 'a'.repeat(64) },
  sample: { id: 'sample_demo', hash: 'b'.repeat(64) },
  structure: {
    id: 'structure_demo',
    hash: 'c'.repeat(64),
    roles: {
      subjectId: 'subject',
      clusterId: 'cluster',
      timeId: 'time',
      groupId: 'group',
      treatmentId: null,
    },
  },
  measurement: null,
  contextHash: 'd'.repeat(64),
} as unknown as ResolvedAnalysisContext

describe('slice-aware advanced templates', () => {
  it('selects the concrete experimental slice instead of defaulting to factorial ANOVA', () => {
    const spec = buildAnalysisSpecTemplate(
      'experimental_design',
      'experimental_design.ancova.long.single_outcome',
      'dataset_demo',
      variables,
      [],
      context,
    ) as Record<string, unknown>

    expect(spec.designType).toBe('ancova')
    expect(spec.covariateIds).toEqual(['x'])
    expect(spec.betweenFactors).toEqual([{ variableId: 'group', coding: 'sum' }])
  })

  it('builds a valid Monte Carlo power shape and aggregation shape for their slices', () => {
    const power = buildAnalysisSpecTemplate(
      'power_analysis',
      'power_analysis.monte_carlo',
      'dataset_demo',
      variables,
      [],
      context,
    ) as Record<string, unknown>
    const aggregation = buildAnalysisSpecTemplate(
      'multilevel_model',
      'multilevel_model.aggregation.icc_rwg',
      'dataset_demo',
      variables,
      [],
      context,
    ) as Record<string, unknown>

    expect(power.method).toBe('monte_carlo')
    expect(power.monteCarloParameters).toBeDefined()
    expect(aggregation.analysisType).toBe('aggregation')
    expect(aggregation.clusterVariableId).toBe('cluster')
    expect((aggregation.scaleItemIds as string[]).length).toBeGreaterThanOrEqual(2)
  })

  it('routes measurement slices to their declared model types', () => {
    const spec = buildAnalysisSpecTemplate(
      'questionnaire_measurement',
      'questionnaire_measurement.measurement_invariance',
      'dataset_demo',
      variables,
      [
        { id: 'construct_a', label: 'A', itemIds: ['y', 'x'] },
        { id: 'construct_b', label: 'B', itemIds: ['age', 'y'] },
      ],
      context,
    ) as Record<string, unknown>

    expect(spec.modelType).toBe('measurement_invariance')
    expect(spec.groupVariableId).toBe('group')
  })

  it('keeps wide repeated-measures defaults compatible with the contract', () => {
    const wideContext = {
      ...context,
      structure: {
        ...context.structure,
        roles: { ...context.structure?.roles, dataLayout: 'wide' },
      },
    } as unknown as ResolvedAnalysisContext
    const spec = buildAnalysisSpecTemplate(
      'experimental_design',
      'experimental_design.repeated_measures.single_within',
      'dataset_demo',
      variables,
      [],
      wideContext,
    ) as Record<string, unknown>

    expect(spec.dataLayout).toBe('wide')
    expect((spec.withinFactors as Array<Record<string, unknown>>)[0].columns).toEqual({
      '1': 'y',
      '2': 'x',
    })
  })
})
