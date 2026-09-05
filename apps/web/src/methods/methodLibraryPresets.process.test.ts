import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

describe('PROCESS method library presets', () => {
  it('exposes common PROCESS forms separately from the full advanced catalog', () => {
    const processMethod = methodDefinitions.find((method) => method.id === 'model.process')
    expect(processMethod).toBeDefined()
    if (!processMethod) throw new Error('model.process registry entry is missing')

    const entries = expandMethodForLibrary(processMethod)
    expect(entries.map((entry) => ({
      id: entry.id,
      processModelNumber: entry.processModelNumber,
      processMediatorCount: entry.processMediatorCount,
      advanced: entry.advanced,
      visibilityTier: entry.visibilityTier,
    }))).toEqual([
      {
        id: 'model.process.simple-mediation',
        processModelNumber: 4,
        processMediatorCount: 1,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.parallel-mediation',
        processModelNumber: 4,
        processMediatorCount: 2,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.serial-mediation',
        processModelNumber: 6,
        processMediatorCount: 2,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.simple-moderation',
        processModelNumber: 1,
        processMediatorCount: undefined,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.first-stage-moderated-mediation',
        processModelNumber: 7,
        processMediatorCount: 1,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.second-stage-moderated-mediation',
        processModelNumber: 14,
        processMediatorCount: 1,
        advanced: false,
        visibilityTier: 'common',
      },
      {
        id: 'model.process.full-catalog',
        processModelNumber: undefined,
        processMediatorCount: undefined,
        advanced: true,
        visibilityTier: 'advanced',
      },
    ])
  })
})