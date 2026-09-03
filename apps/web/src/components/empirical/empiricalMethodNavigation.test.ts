import { describe, expect, it } from 'vitest'

import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import { configForMethod } from './empiricalMethodNavigation'

const baseConfig = {
  longitudinalPanel: null,
  diaryMultilevel: null,
} as EmpiricalConfigValue

describe('configForMethod direct longitudinal and diary routing', () => {
  it('opens traditional CLPM with the supported two-wave starting point', () => {
    const config = configForMethod(baseConfig, 'empirical.panel.clpm', null)
    expect(config.longitudinalPanel?.modelType).toBe('clpm')
    expect(config.longitudinalPanel?.waves).toHaveLength(2)
    expect(config.diaryMultilevel).toBeNull()
  })

  it.each([
    ['empirical.panel.ri_clpm', 'ri_clpm'],
    ['empirical.panel.lcm_sr', 'lcm_sr'],
  ] as const)('opens %s with a three-wave starting point', (sliceId, modelType) => {
    const config = configForMethod(baseConfig, sliceId, null)
    expect(config.longitudinalPanel?.modelType).toBe(modelType)
    expect(config.longitudinalPanel?.waves).toHaveLength(3)
  })

  it('routes DSEM directly to the diary DSEM configuration', () => {
    const config = configForMethod(baseConfig, 'empirical.diary.dsem', null)
    expect(config.longitudinalPanel).toBeNull()
    expect(config.diaryMultilevel?.analysisType).toBe('dsem')
    expect(config.diaryMultilevel?.dsem).not.toBeNull()
  })
})
