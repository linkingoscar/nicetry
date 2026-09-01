import type { MeasurementVersion, ModelSpec, ModelVariable } from '../../types'
import { nodeFromVariable } from './modelTemplates'

export function buildModelForEstimationFamily(
  current: ModelSpec,
  family: 'ols' | 'sem',
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  if (current.estimation.family === family) return current
  if (family === 'sem') {
    const latentDefinitions = current.nodes.flatMap((node) => {
      const construct = measurement.constructs.find(
        (candidate) => candidate.outputVariableId === node.variableId,
      )
      return construct
        ? [{ id: node.id, name: node.label, level: 'first_order' as const, indicators: [...construct.itemIds] }]
        : []
    })
    const latentIds = new Set(latentDefinitions.map((latent) => latent.id))
    return {
      ...current,
      nodes: current.nodes.map((node) => latentIds.has(node.id)
        ? { ...node, variableId: undefined, kind: 'latent', dataType: 'continuous' }
        : node),
      latents: latentDefinitions,
      estimation: {
        ...current.estimation,
        family: 'sem',
        estimator: 'ML',
        groupVariableId: null,
        invariance: false,
        multiGroup: {
          compareStructuralPaths: false,
          estimateLatentMeans: false,
        },
        standardErrors: 'standard',
        missing: 'fiml',
      },
    }
  }

  const latentById = new Map((current.latents ?? []).map((latent) => [latent.id, latent]))
  return {
    ...current,
    nodes: current.nodes.map((node) => {
      const latent = latentById.get(node.id)
      if (!latent) return node
      const construct = measurement.constructs.find((candidate) =>
        candidate.name === latent.name
        || (candidate.itemIds.length === latent.indicators.length
          && candidate.itemIds.every((itemId) => latent.indicators.includes(itemId))),
      )
      const variable = variables.find((candidate) => candidate.id === construct?.outputVariableId)
      return variable ? { ...nodeFromVariable(node.role, variable), id: node.id } : node
    }),
    latents: undefined,
    estimation: {
      ...current.estimation,
      family: 'ols',
      estimator: undefined,
      groupVariableId: undefined,
      invariance: undefined,
      standardErrors: 'hc3',
      missing: 'complete_cases_per_model',
    },
  }
}
