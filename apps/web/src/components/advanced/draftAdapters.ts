import type { ResolvedAnalysisContext } from '../../types/analysis-context'

export type DraftRoleDefaults = {
  subjectId?: string
  clusterId?: string
  timeId?: string
  groupId?: string
  treatmentId?: string
}

export type DraftRoleOverrideCandidate = {
  role: keyof DraftRoleDefaults
  variableId: string
}

export function adaptMultilevelDraft(context: ResolvedAnalysisContext): DraftRoleDefaults {
  return context.structure?.roles.clusterId ? { clusterId: context.structure.roles.clusterId } : {}
}

export function adaptExperimentDraft(context: ResolvedAnalysisContext): DraftRoleDefaults {
  const roles = context.structure?.roles
  return {
    subjectId: roles?.subjectId ?? undefined,
    timeId: roles?.timeId ?? undefined,
    groupId: roles?.groupId ?? undefined,
    treatmentId: roles?.treatmentId ?? undefined,
    clusterId: roles?.clusterId ?? undefined,
  }
}

export function adaptImputationDraft(context: ResolvedAnalysisContext): DraftRoleDefaults {
  return context.structure?.roles.clusterId ? { clusterId: context.structure.roles.clusterId } : {}
}

export function adaptDraftRoles(sliceId: string, context: ResolvedAnalysisContext): DraftRoleDefaults {
  if (sliceId.startsWith('multilevel_model.') || sliceId.startsWith('empirical.diary.cross_classified')) {
    return adaptMultilevelDraft(context)
  }
  if (sliceId.startsWith('multiple_imputation.')) return adaptImputationDraft(context)
  if (sliceId.startsWith('experimental_design.')) return adaptExperimentDraft(context)
  if (sliceId.startsWith('questionnaire_measurement.')) {
    const roles = context.structure?.roles
    return {
      groupId: roles?.groupId ?? undefined,
      treatmentId: roles?.treatmentId ?? undefined,
    }
  }
  return {}
}

function addCandidate(
  candidates: Map<keyof DraftRoleDefaults, string>,
  role: keyof DraftRoleDefaults,
  value: unknown,
  defaults: DraftRoleDefaults,
  allowed: Set<keyof DraftRoleDefaults>,
) {
  if (allowed.has(role) && typeof value === 'string' && value && value !== defaults[role]) {
    candidates.set(role, value)
  }
}

/**
 * Extract explicit role changes from a validated advanced spec. This is kept
 * separate from the UI so role lineage can be tested without rendering the
 * complete wizard.
 */
export function collectDraftRoleOverrides(
  sliceId: string,
  spec: Record<string, unknown>,
  context: ResolvedAnalysisContext,
): DraftRoleOverrideCandidate[] {
  const defaults = adaptDraftRoles(sliceId, context)
  const candidates = new Map<keyof DraftRoleDefaults, string>()
  const allowed = new Set<keyof DraftRoleDefaults>()
  if (sliceId.startsWith('multilevel_model.')) allowed.add('clusterId')
  if (sliceId.startsWith('experimental_design.')) {
    allowed.add('groupId')
    allowed.add('treatmentId')
    if (sliceId.includes('.repeated_measures.') || sliceId.includes('.mixed_design.')) {
      allowed.add('subjectId')
      allowed.add('timeId')
    }
    if (sliceId.includes('.glm_cluster.')) allowed.add('clusterId')
  }
  if (sliceId === 'questionnaire_measurement.measurement_invariance') allowed.add('groupId')
  const roles = spec.roles && typeof spec.roles === 'object'
    ? spec.roles as Record<string, unknown>
    : {}

  addCandidate(candidates, 'subjectId', spec.subjectId ?? roles.subjectId, defaults, allowed)
  addCandidate(candidates, 'clusterId', spec.clusterVariableId ?? roles.clusterId, defaults, allowed)
  addCandidate(candidates, 'timeId', spec.timeVariableId ?? roles.timeId, defaults, allowed)
  addCandidate(candidates, 'groupId', spec.groupVariableId ?? roles.groupId, defaults, allowed)
  addCandidate(candidates, 'treatmentId', spec.treatmentVariableId ?? roles.treatmentId, defaults, allowed)

  const betweenFactors = Array.isArray(spec.betweenFactors) ? spec.betweenFactors : []
  const firstFactor = betweenFactors[0]
  if (firstFactor && typeof firstFactor === 'object') {
    const factorVariableId = (firstFactor as Record<string, unknown>).variableId
    const factorRole = defaults.treatmentId ? 'treatmentId' : 'groupId'
    addCandidate(candidates, factorRole, factorVariableId, defaults, allowed)
  }

  return Array.from(candidates, ([role, variableId]) => ({ role, variableId }))
}
