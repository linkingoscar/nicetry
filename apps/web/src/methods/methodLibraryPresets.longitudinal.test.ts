import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

describe('longitudinal method catalog copy', () => {
  it('keeps the authoritative three-wave CLPM boundary from the method registry', () => {
    const source = methodDefinitions.find((method) => method.id === 'longitudinal.clpm')
    if (!source) throw new Error('Missing longitudinal.clpm')
    const method = expandMethodForLibrary(source)[0]

    expect(method.description).toBe(source.description)
    expect(method.description).toContain('至少三波')
    expect(method.capabilitySliceIds).toEqual(source.capabilitySliceIds)
  })
})
