import type { ModelSpec, ResultBundle } from '../../types'
import { loadingEdgeId } from './semCanvasGraph'

export type EvidenceStatus = 'idle' | 'running' | 'inference_signal' | 'inference_uncertain' | 'unavailable'

export interface PathEvidence {
  estimate?: number
  standardError?: number | null
  statistic?: number | null
  pValue?: number | null
  lower?: number | null
  upper?: number | null
  status: EvidenceStatus
}

function statusFor(pValue?: number | null, lower?: number | null, upper?: number | null): EvidenceStatus {
  if (typeof lower === 'number' && typeof upper === 'number') {
    return lower > 0 || upper < 0 ? 'inference_signal' : 'inference_uncertain'
  }
  if (typeof pValue === 'number') return pValue < 0.05 ? 'inference_signal' : 'inference_uncertain'
  return 'unavailable'
}

export function buildPathEvidence(
  model: ModelSpec,
  result: ResultBundle | undefined,
  running: boolean,
): Record<string, PathEvidence> {
  if (running) {
    return Object.fromEntries([
      ...model.edges.map((edge) => [edge.id, { status: 'running' as const }]),
      ...model.moderations.map((moderation) => [`moderation:${moderation.id}`, { status: 'running' as const }]),
      ...(model.latents ?? []).flatMap(latent => latent.indicators.map(indicator => [loadingEdgeId(latent.id, indicator), { status: 'running' as const }])),
    ])
  }
  if (!result) return {}

  const evidence: Record<string, PathEvidence> = {}
  const semName = (id: string) => {
    const node = model.nodes?.find(item => item.id === id)
    return node?.kind === 'latent' ? id : node?.variableId ?? id
  }
  for (const latent of model.latents ?? []) {
    for (const indicator of latent.indicators) {
      const loading = result.semResult?.loadings?.find(item => item.latentId === latent.id && item.indicatorId === semName(indicator))
      if (loading) evidence[loadingEdgeId(latent.id, indicator)] = {
        estimate: loading.estimate, standardError: loading.standardError, statistic: loading.statistic,
        pValue: loading.pValue, lower: loading.ciLower, upper: loading.ciUpper,
        status: statusFor(loading.pValue, loading.ciLower, loading.ciUpper),
      }
    }
  }
  for (const edge of model.edges) {
    const semPath = result.semResult?.paths.find((path) => path.from === semName(edge.from) && path.to === semName(edge.to))
    if (semPath) {
      evidence[edge.id] = {
        estimate: semPath.estimate,
        standardError: semPath.standardError,
        statistic: semPath.statistic,
        pValue: semPath.pValue,
        lower: semPath.ciLower,
        upper: semPath.ciUpper,
        status: statusFor(semPath.pValue, semPath.ciLower, semPath.ciUpper),
      }
      continue
    }
    const equation = result.equations.find((item) => item.formula.trimStart().startsWith(`${edge.to} ~`))
    const coefficient = equation?.coefficients?.find((item) => item.term === edge.from)
    const interval = coefficient?.confidenceInterval
    evidence[edge.id] = coefficient
      ? {
          estimate: coefficient.estimate,
          standardError: coefficient.standardError,
          statistic: coefficient.statistic,
          pValue: coefficient.pValue,
          lower: interval?.lower,
          upper: interval?.upper,
          status: statusFor(coefficient.pValue, interval?.lower, interval?.upper),
        }
      : { status: 'unavailable' }
  }

  for (const moderation of model.moderations) {
    const edge = model.edges.find((item) => item.id === moderation.targetEdgeId)
    const equation = edge
      ? result.equations.find((item) => item.formula.trimStart().startsWith(`${edge.to} ~`))
      : undefined
    const coefficient = equation?.coefficients?.find((item) => item.term === moderation.productTermId)
    const interval = coefficient?.confidenceInterval
    evidence[`moderation:${moderation.id}`] = coefficient
      ? {
          estimate: coefficient.estimate,
          standardError: coefficient.standardError,
          statistic: coefficient.statistic,
          pValue: coefficient.pValue,
          lower: interval?.lower,
          upper: interval?.upper,
          status: statusFor(coefficient.pValue, interval?.lower, interval?.upper),
        }
      : { status: 'unavailable' }
  }
  return evidence
}
