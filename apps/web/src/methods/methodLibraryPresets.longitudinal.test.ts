import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

describe('longitudinal method catalog copy', () => {
  it('describes CLPM using the same two-wave boundary as the current form', () => {
    const source = methodDefinitions.find((method) => method.id === 'longitudinal.clpm')
    if (!source) throw new Error('Missing longitudinal.clpm')
    const method = expandMethodForLibrary(source)[0]

    expect(method.description).toContain('两时点 CLPM')
    expect(method.description).toContain('三时点及以上')
    expect(method.description).not.toContain('至少三波')
    expect(method.capabilitySliceIds).toEqual(source.capabilitySliceIds)
  })
})
