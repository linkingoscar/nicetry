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
]

describe('common advanced-form discovery', () => {
  it('keeps high-frequency form-based methods in the common method tier', () => {
    commonIds.forEach((id) => {
      const definition = methodDefinitions.find((method) => method.id === id)
      expect(definition, id).toBeDefined()
      expect(expandMethodForLibrary(definition!)[0]).toMatchObject({
        id,
        visibilityTier: 'common',
        advanced: false,
      })
    })
  })

  it('does not globally demote unrelated advanced methods', () => {
    const definition = methodDefinitions.find((method) => method.id === 'measurement.esem-bifactor-irt')
    expect(definition).toBeDefined()
    expect(expandMethodForLibrary(definition!)[0]).toMatchObject({
      visibilityTier: 'advanced',
      advanced: true,
    })
  })
})
