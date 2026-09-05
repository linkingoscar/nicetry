import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

const commonIds = [
  'experiment.factorial-anova',
  'experiment.ancova',
  'experiment.repeated-measures',
  'experiment.mixed-design',
  'multilevel.aggregation',
  'multilevel.gaussian-lmm',
  'power.regression',
  'power.t-test',
  'power.factorial-anova',
]

describe('common advanced-form discovery', () => {
  it('keeps high-frequency form-based methods in the common method tier', () => {
    commonIds.forEach((id) => {
      const definition = methodDefinitions.find((method) => method.id === id)
      expect(definition, id).toBeDefined()
      if (!definition) throw new Error(`method registry entry is missing: ${id}`)
      expect(expandMethodForLibrary(definition)[0]).toMatchObject({
        id,
        visibilityTier: 'common',
        advanced: false,
      })
    })
  })

  it('does not globally demote unrelated advanced methods', () => {
    const definition = methodDefinitions.find((method) => method.id === 'measurement.esem-bifactor-irt')
    expect(definition).toBeDefined()
    if (!definition) throw new Error('measurement.esem-bifactor-irt registry entry is missing')
    expect(expandMethodForLibrary(definition)[0]).toMatchObject({
      visibilityTier: 'advanced',
      advanced: true,
    })
  })
})