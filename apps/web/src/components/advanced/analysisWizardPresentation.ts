import type { AdvancedAnalysisCapability } from '../../types'

export type AnalysisWizardPresentation = 'standard' | 'advanced'

const STANDARD_FORM_SLICES = new Set([
  'experimental_design.factorial_anova.long.single_outcome',
  'experimental_design.ancova.long.single_outcome',
  'experimental_design.repeated_measures.single_within',
  'experimental_design.mixed_design.single_within',
  'multilevel_model.aggregation.icc_rwg',
  'multilevel_model.gaussian.two_level',
  'power_analysis.analytic.regression',
  'power_analysis.analytic.t_test',
  'power_analysis.analytic.factorial_anova',
])

export function analysisWizardPresentation(
  capability: Pick<AdvancedAnalysisCapability, 'sliceId'>,
): AnalysisWizardPresentation {
  return capability.sliceId && STANDARD_FORM_SLICES.has(capability.sliceId)
    ? 'standard'
    : 'advanced'
}
