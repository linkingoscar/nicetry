import type { ModelSpec } from '../../types'

/** Remove measurement definitions atomically, retaining surviving factors for validation. */
export function removeLatentDefinitions(model: ModelSpec, ids: string[]): ModelSpec {
  if (!model.latents) return model
  const removed = new Set(ids)
  const latents = model.latents.filter(latent => !removed.has(latent.id)).map(latent => ({
    ...latent,
    indicators: latent.indicators.filter(id => !removed.has(id)),
  }))
  const observedIndicators = new Set(latents.filter(latent => latent.level !== 'higher_order').flatMap(latent => latent.indicators))
  const multiGroup = model.estimation.multiGroup
  return {
    ...model,
    latents,
    estimation: {
      ...model.estimation,
      ...(multiGroup ? { multiGroup: {
        ...multiGroup,
        partialInvarianceReleases: multiGroup.partialInvarianceReleases?.filter(release =>
          release.constraint === 'loading'
            ? latents.some(latent => latent.id === release.latentId && latent.indicators.includes(release.indicatorId))
            : observedIndicators.has(release.indicatorId)),
      } } : {}),
    },
  }
}
