import { describe, expect, it } from 'vitest'

import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { collectDraftRoleOverrides } from './draftAdapters'

const context = {
  structure: {
    roles: {
      subjectId: 'subject_default',
      clusterId: 'cluster_default',
      timeId: 'time_default',
      groupId: 'group_default',
      treatmentId: null,
    },
  },
} as unknown as ResolvedAnalysisContext

describe('advanced draft role lineage', () => {
  it('records explicit cluster changes against structure defaults', () => {
    const overrides = collectDraftRoleOverrides(
      'multilevel_model.gaussian.two_level',
      {
        clusterVariableId: 'cluster_override',
      },
      context,
    )

    expect(overrides).toEqual([
      { role: 'clusterId', variableId: 'cluster_override' },
    ])
  })

  it('does not create an override for the context default binding', () => {
    const overrides = collectDraftRoleOverrides(
      'experimental_design.factorial_anova.long.single_outcome',
      { subjectId: 'subject_default', betweenFactors: [{ variableId: 'group_default' }] },
      context,
    )

    expect(overrides).toEqual([])
  })
})
