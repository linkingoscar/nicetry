import { describe, expect, it } from 'vitest'

import type { ApplicableCapability } from '../../types/analysis-context'
import { methodDefinitions } from '../../methods/methodDefinitions'
import { expandMethodForLibrary } from '../../methods/methodLibraryPresets'
import { internalWorkbenchTarget } from './contextCapabilityCatalogUtils'

describe('PROCESS workbench routing', () => {
  it('carries the preferred PROCESS model number from the library entry into the model request', () => {
    const processMethod = methodDefinitions.find((method) => method.id === 'model.process')
    expect(processMethod).toBeDefined()
    const mediation = expandMethodForLibrary(processMethod!).find((method) => method.processModelNumber === 4)
    const moderation = expandMethodForLibrary(processMethod!).find((method) => method.processModelNumber === 1)
    const capability = {
      sliceId: 'model.process_catalog',
      executionAvailable: true,
    } as unknown as ApplicableCapability

    expect(internalWorkbenchTarget(capability, mediation)).toMatchObject({
      view: 'model',
      sliceId: 'model.process_catalog',
      processModelNumber: 4,
      label: '简单中介（PROCESS Model 4）',
    })
    expect(internalWorkbenchTarget(capability, moderation)).toMatchObject({
      view: 'model',
      sliceId: 'model.process_catalog',
      processModelNumber: 1,
      label: '简单调节（PROCESS Model 1）',
    })
  })
})
