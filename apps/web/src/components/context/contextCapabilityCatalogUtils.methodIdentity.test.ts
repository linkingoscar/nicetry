import { describe, expect, it } from 'vitest'

import { methodDefinitions } from '../../methods/methodDefinitions'
import { expandMethodForLibrary } from '../../methods/methodLibraryPresets'
import type { ApplicableCapability } from '../../types/analysis-context'
import { internalWorkbenchTarget } from './contextCapabilityCatalogUtils'

function capability(sliceId: string): ApplicableCapability {
  return { sliceId, executionAvailable: true } as ApplicableCapability
}

function method(id: string) {
  const source = methodDefinitions.find((entry) => entry.id === id)
  if (!source) throw new Error(`Missing method ${id}`)
  return source
}

describe('internalWorkbenchTarget method identity', () => {
  it('carries a concrete longitudinal method id and procedure into the empirical workbench', () => {
    const definition = expandMethodForLibrary(method('longitudinal.clpm'))[0]
    expect(internalWorkbenchTarget(capability('empirical.panel.clpm'), definition)).toMatchObject({
      view: 'empirical',
      tab: 'longitudinal',
      sliceId: 'empirical.panel.clpm',
      methodId: 'longitudinal.clpm',
      procedure: 'longitudinal',
    })
  })

  it('carries diary method identity instead of relying on the editor to infer the procedure later', () => {
    const definition = expandMethodForLibrary(method('diary.dsem'))[0]
    expect(internalWorkbenchTarget(capability('empirical.diary.dsem'), definition)).toMatchObject({
      view: 'empirical',
      tab: 'diary',
      methodId: 'diary.dsem',
      procedure: 'diary',
    })
  })

  it('keeps direct empirical presets on their exact library method id and procedure', () => {
    const frequency = expandMethodForLibrary(method('empirical.overview')).find((entry) => entry.procedure === 'frequencies')
    if (!frequency) throw new Error('Missing frequencies preset')
    expect(internalWorkbenchTarget(capability('empirical.cross_sectional.overview'), frequency)).toMatchObject({
      methodId: 'empirical.overview.frequencies',
      procedure: 'frequencies',
    })
  })
})
