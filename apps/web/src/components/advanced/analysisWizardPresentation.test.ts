import { describe, expect, it } from 'vitest'

import type { AdvancedAnalysisCapability } from '../../types'
import { analysisWizardPresentation } from './analysisWizardPresentation'

function capability(sliceId: string): AdvancedAnalysisCapability {
  return { sliceId } as AdvancedAnalysisCapability
}

describe('analysisWizardPresentation', () => {
  it.each([
    'experimental_design.factorial_anova.long.single_outcome',
    'experimental_design.ancova.long.single_outcome',
    'experimental_design.repeated_measures.single_within',
    'experimental_design.mixed_design.single_within',
    'multilevel_model.aggregation.icc_rwg',
    'multilevel_model.gaussian.two_level',
    'power_analysis.analytic.regression',
    'power_analysis.analytic.t_test',
    'power_analysis.analytic.factorial_anova',
  ])('uses the standard form presentation for %s', (sliceId) => {
    expect(analysisWizardPresentation(capability(sliceId))).toBe('standard')
  })

  it.each([
    'questionnaire_measurement.esem_bifactor_irt',
    'power_analysis.monte_carlo',
  ])('keeps specialist method %s in the advanced presentation', (sliceId) => {
    expect(analysisWizardPresentation(capability(sliceId))).toBe('advanced')
  })
})
