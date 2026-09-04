import { describe, expect, it } from 'vitest'

import type { ApplicableCapability } from '../../types/analysis-context'
import { methodDefinitions } from '../../methods/methodDefinitions'
import { expandMethodForLibrary } from '../../methods/methodLibraryPresets'
import { internalWorkbenchTarget } from './contextCapabilityCatalogUtils'

describe('PROCESS workbench routing', () => {
  it('carries common PROCESS model identity from the library entry into the model request', () => {
    const processMethod = methodDefinitions.find((method) => method.id === 'model.process')
    expect(processMethod).toBeDefined()
    const entries = expandMethodForLibrary(processMethod!)
    const capability = {
      sliceId: 'model.process_catalog',
      executionAvailable: true,
    } as unknown as ApplicableCapability

    const expected = [
      ['model.process.simple-mediation', 4, 1, '简单中介（PROCESS Model 4）'],
      ['model.process.parallel-mediation', 4, 2, '并行中介（PROCESS Model 4）'],
      ['model.process.serial-mediation', 6, 2, '链式中介（PROCESS Model 6）'],
      ['model.process.simple-moderation', 1, undefined, '简单调节（PROCESS Model 1）'],
      ['model.process.first-stage-moderated-mediation', 7, 1, '第一阶段调节中介（PROCESS Model 7）'],
      ['model.process.second-stage-moderated-mediation', 14, 1, '第二阶段调节中介（PROCESS Model 14）'],
    ] as const

    expected.forEach(([id, processModelNumber, processMediatorCount, label]) => {
      const method = entries.find((entry) => entry.id === id)
      expect(internalWorkbenchTarget(capability, method)).toMatchObject({
        view: 'model',
        sliceId: 'model.process_catalog',
        methodId: id,
        processModelNumber,
        ...(processMediatorCount ? { processMediatorCount } : {}),
        label,
      })
    })
  })
})
