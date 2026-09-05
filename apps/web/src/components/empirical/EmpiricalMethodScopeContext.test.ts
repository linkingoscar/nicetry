import { describe, expect, it } from 'vitest'

import {
  lockedDiaryAnalysisType,
  lockedLongitudinalModelType,
} from './EmpiricalMethodScopeContext'

describe('empirical method scope locks', () => {
  it.each([
    ['empirical.panel.clpm', 'clpm'],
    ['empirical.panel.ri_clpm', 'ri_clpm'],
    ['empirical.panel.lcm_sr', 'lcm_sr'],
  ] as const)('locks %s to %s', (sliceId, modelType) => {
    expect(lockedLongitudinalModelType(sliceId)).toBe(modelType)
  })

  it('leaves longitudinal diagnostic methods free to choose their target panel model', () => {
    expect(lockedLongitudinalModelType('empirical.panel.invariance')).toBeNull()
    expect(lockedLongitudinalModelType('empirical.panel.ulmc_sensitivity')).toBeNull()
  })

  it.each([
    ['empirical.diary.lmm', 'lmm'],
    ['empirical.diary.glmm', 'glmm'],
    ['empirical.diary.multilevel_mediation', 'mediation'],
    ['empirical.diary.dsem', 'bayesian_dsem'],
    ['empirical.diary.cross_classified_gaussian', 'lmm'],
    ['empirical.diary.mi', 'lmm'],
    ['empirical.diary.power', 'lmm'],
  ] as const)('locks %s to %s', (sliceId, analysisType) => {
    expect(lockedDiaryAnalysisType(sliceId)).toBe(analysisType)
  })
})
