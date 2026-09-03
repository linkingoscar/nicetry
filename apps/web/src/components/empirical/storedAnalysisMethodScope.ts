import { methodDefinitions } from '../../methods/methodDefinitions'

const METHOD_SCOPED_EMPIRICAL_ADAPTERS = new Set([
  'empirical-longitudinal',
  'empirical-diary',
])

export function storedAnalysisMethodSlice(methodId?: string | null): string | undefined {
  if (!methodId) return undefined
  const method = methodDefinitions.find((definition) => definition.id === methodId)
  if (!method || !METHOD_SCOPED_EMPIRICAL_ADAPTERS.has(method.adapter)) return undefined
  return method.capabilitySliceIds.length === 1 ? method.capabilitySliceIds[0] : undefined
}
