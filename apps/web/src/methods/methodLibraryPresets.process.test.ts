import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

describe('PROCESS method library presets', () => {
  it('exposes simple mediation, simple moderation, and the full advanced catalog separately', () => {
    const processMethod = methodDefinitions.find((method) => method.id === 'model.process')
    expect(processMethod).toBeDefined()

    const entries = expandMethodForLibrary(processMethod!)
    expect(entries.map((entry) => ({
      id: entry.id,
      processModelNumber: entry.processModelNumber,
      advanced: entry.advanced,
      visibilityTier: entry.visibilityTier,
    }))).toEqual([
      {
        id: 'model.process.simple-mediation',
        processModelNumber: 4,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.simple-moderation',
        processModelNumber: 1,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.full-catalog',
        processModelNumber: undefined,
        advanced: true,
        visibilityTier: 'advanced',
      },
    ])
  })
})
