import registryJson from './methodRegistry.json'

export type MethodEntryKind = 'empirical-procedure' | 'process-catalog' | 'sem' | 'advanced-wizard'
export type MethodAdapter =
  | 'empirical-overview'
  | 'empirical-measurement'
  | 'empirical-groups'
  | 'empirical-regression'
  | 'empirical-advanced'
  | 'empirical-longitudinal'
  | 'empirical-diary'
  | 'model'
  | 'advanced-wizard'
export type MethodResultKind = 'empirical' | 'model' | 'advanced'
export type MethodVisibilityTier = 'common' | 'standard' | 'advanced' | 'internal'

export interface MethodDefinition {
  id: string
  label: string
  aliases: string[]
  categoryId: string
  description: string
  keywords: string[]
  entryKind: MethodEntryKind
  capabilitySliceIds: string[]
  consumerCapabilitySliceIds: string[]
  adapter: MethodAdapter
  resultKind: MethodResultKind
  visibilityTier: MethodVisibilityTier
  advanced: boolean
  experimental: boolean
  supportsNoDataset: boolean
}

interface MethodRegistryDocument {
  schemaVersion: string
  methods: MethodDefinition[]
}

const registry = registryJson as MethodRegistryDocument

export const METHOD_REGISTRY_SCHEMA_VERSION = registry.schemaVersion
export const methodDefinitions = registry.methods

export function methodForCapability(sliceId: string): MethodDefinition | undefined {
  return methodDefinitions.find((method) => method.capabilitySliceIds.includes(sliceId))
}

export function methodSearchText(method: MethodDefinition): string {
  return [method.label, method.description, ...method.aliases, ...method.keywords].join(' ').toLocaleLowerCase()
}
