import { describe, expect, it } from 'vitest'

import { methodDefinitions } from './methodDefinitions'
import { expandMethodForLibrary } from './methodLibraryPresets'

function method(id: string) {
  const definition = methodDefinitions.find((entry) => entry.id === id)
  if (!definition) throw new Error(`Missing method ${id}`)
  return definition
}

describe('advanced measurement method labels', () => {
  it.each([
    ['measurement.ordinal-reliability', '高级序数信度'],
    ['measurement.polychoric-efa', '高级 EFA'],
    ['measurement.cfa', '高级 CFA'],
    ['measurement.invariance', '高级多组测量等值性'],
    ['measurement.common-method-bias', '高级共同方法偏差'],
  ])('keeps %s discoverable as an explicitly advanced variant', (methodId, labelFragment) => {
    const source = method(methodId)
    const expanded = expandMethodForLibrary(source)[0]

    expect(expanded.label).toContain(labelFragment)
    expect(expanded.visibilityTier).toBe(source.visibilityTier)
    expect(expanded.advanced).toBe(source.advanced)
    expect(expanded.capabilitySliceIds).toEqual(source.capabilitySliceIds)
  })

  it('keeps the common empirical measurement methods concise and unchanged', () => {
    const expanded = expandMethodForLibrary(method('empirical.measurement'))
    const labels = Object.fromEntries(expanded.map((entry) => [entry.procedure, entry.label]))

    expect(labels).toMatchObject({
      reliability: '信度与项目分析',
      efa: '探索性因子分析（EFA）',
      cfa: '验证性因子分析（CFA）',
      invariance: '多组测量等值性',
      common_method: '共同方法偏差诊断',
    })
  })

  it('marks the specialist measurement bundle itself as advanced in the visible label', () => {
    const source = method('measurement.esem-bifactor-irt')
    const expanded = expandMethodForLibrary(source)[0]
    expect(expanded.label).toContain('（高级）')
    expect(expanded.capabilitySliceIds).toEqual(source.capabilitySliceIds)
  })
})
