import { describe, expect, it } from 'vitest'
import { configForMethod } from './empiricalMethodNavigation'
import { createDiaryMultilevelDefault } from './DiaryMultilevelConfigSections'
import { createDefaultPanel } from './LongitudinalPanelConfig.utils'
import { deriveEmpiricalState, initialEmpiricalConfig } from './empiricalStateDerived'
import type { DatasetVersion } from '../../types'

function config() {
  const derived = deriveEmpiricalState({ variables: [] } as unknown as DatasetVersion, null, null)
  return initialEmpiricalConfig(null, derived, 'questionnaire')
}

describe('catalog method selection', () => {
  it('preserves custom waves and expands only missing LCM-SR waves', () => {
    const base = { ...config(), longitudinalPanel: createDefaultPanel([]) }
    base.longitudinalPanel.waves[0] = { ...base.longitudinalPanel.waves[0], label: 'baseline', xItemIds: ['q1', 'q2', 'q3'] }
    const next = configForMethod(base, 'empirical.panel.lcm_sr')
    expect(next.longitudinalPanel?.waves).toHaveLength(5)
    expect(next.longitudinalPanel?.waves[0]).toEqual(base.longitudinalPanel.waves[0])
    expect(next.longitudinalPanel?.measurementMode).toBe('latent_items')
    expect(base.longitudinalPanel.modelType).toBe('ri_clpm')
    expect(configForMethod(next, 'empirical.panel.lcm_sr')).toEqual(next)
  })

  it('normalizes incompatible GLMM settings when selecting DSEM, retaining variables', () => {
    const diary = { ...createDiaryMultilevelDefault([]), analysisType: 'glmm' as const,
      outcomeVariableId: 'y', predictorVariableId: 'x', outcomeFamily: 'poisson' as const,
      countModel: 'zero_inflated' as const, clusterStructure: 'cross_classified' as const,
      crossClassVariableId: 'site', exposureVariableId: 'minutes', missingStrategy: 'multilevel_mi' as const }
    const base = { ...config(), diaryMultilevel: diary }
    const next = configForMethod(base, 'empirical.diary.dsem')
    expect(next.diaryMultilevel).toMatchObject({ analysisType: 'bayesian_dsem', outcomeFamily: 'gaussian',
      countModel: 'standard', clusterStructure: 'nested', crossClassVariableId: null,
      exposureVariableId: null, missingStrategy: 'complete_cases', temporalEffect: 'lagged',
      outcomeVariableId: 'y', predictorVariableId: 'x', dsem: { chains: 4, iterations: 2000 } })
    expect(base.diaryMultilevel).toEqual(diary)
    expect(configForMethod(next, 'empirical.diary.dsem')).toEqual(next)
  })

  it('sets the requested diagnostic options and keeps independent defaults unchanged', () => {
    const base = config()
    expect(configForMethod(base, 'empirical.panel.ulmc_sensitivity').longitudinalPanel).toMatchObject({ measurementMode: 'latent_items', cmbSensitivity: 'global_ulmc' })
    expect(configForMethod(base, 'empirical.diary.mi').diaryMultilevel?.missingStrategy).toBe('multilevel_mi')
    expect(configForMethod(base, 'empirical.diary.power').diaryMultilevel?.powerAnalysis).not.toBeNull()
    expect(base.diaryMultilevel).toBeNull()
  })

  it('opens traditional CLPM with the capability-catalog three-wave minimum', () => {
    const next = configForMethod(config(), 'empirical.panel.clpm', null)
    expect(next.longitudinalPanel?.modelType).toBe('clpm')
    expect(next.longitudinalPanel?.waves).toHaveLength(3)
  })

  it('opens RI-CLPM with a three-wave starting point', () => {
    const next = configForMethod(config(), 'empirical.panel.ri_clpm', null)
    expect(next.longitudinalPanel?.modelType).toBe('ri_clpm')
    expect(next.longitudinalPanel?.waves).toHaveLength(3)
  })

  it('opens LCM-SR with its five-wave minimum', () => {
    const next = configForMethod(config(), 'empirical.panel.lcm_sr', null)
    expect(next.longitudinalPanel?.modelType).toBe('lcm_sr')
    expect(next.longitudinalPanel?.waves).toHaveLength(5)
    expect(next.longitudinalPanel?.measurementMode).toBe('latent_items')
  })

  it('routes DSEM directly to the Bayesian diary DSEM configuration', () => {
    const next = configForMethod(config(), 'empirical.diary.dsem', null)
    expect(next.diaryMultilevel?.analysisType).toBe('bayesian_dsem')
    expect(next.diaryMultilevel?.dsem).not.toBeNull()
  })
})
