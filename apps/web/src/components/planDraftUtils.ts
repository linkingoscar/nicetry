import type { StudyContext } from '../types/study-context'
import type { StudyPlanVersion } from '../types/workflows'

export interface PlannedRoleDraft {
  uiId: string
  key: string
  label: string
  role: string
  level: number
  acceptedTypes: string
  structureRole: string
}

export interface ConstructDraft {
  uiId: string
  id: string
  label: string
  itemIds: string
}

export interface RobustnessDraft {
  uiId: string
  sliceId: string
  rationale: string
}

export interface PlanDraft {
  title: string
  researchQuestion: string
  hypothesis: string
  estimand: string
  missingDataStrategy: string
  sliceId: string
  plannedRoles: PlannedRoleDraft[]
  constructs: ConstructDraft[]
  robustnessAnalyses: RobustnessDraft[]
  effectSize: number
  alpha: number
  targetPower: number
  predictors: number
  groups: number
  solveFor: 'sample_size' | 'power' | 'effect_size'
}

export const PRIMARY_ANALYSIS_OPTIONS = [
  ['power_analysis.analytic.regression', '解析功效：回归'],
  ['power_analysis.analytic.t_test', '解析功效：t 检验'],
  ['power_analysis.analytic.factorial_anova', '解析功效：组间 ANOVA'],
  ['questionnaire_measurement.reliability', '横截面测量：信度'],
  ['experimental_design.factorial_anova.long.single_outcome', '实验设计：组间 factorial ANOVA'],
  ['multilevel_model.gaussian.two_level', '嵌套数据：两层 Gaussian LMM'],
  ['multiple_imputation.rubin_pooling', '缺失数据：Rubin 合并推断'],
] as const

export const PLANNING_FAMILIES = [
  'power_analysis',
  'experimental_design',
  'multilevel_model',
  'multiple_imputation',
  'questionnaire_measurement',
]

let draftItemSequence = 0

export function nextDraftItemId(prefix: string): string {
  draftItemSequence += 1
  return `${prefix}-${draftItemSequence}`
}

export const EMPTY_DRAFT: PlanDraft = {
  title: '',
  researchQuestion: '',
  hypothesis: '',
  estimand: '',
  missingDataStrategy: '完整案例分析；如缺失超过预设阈值则转入多重插补敏感性分析',
  sliceId: PRIMARY_ANALYSIS_OPTIONS[0][0],
  plannedRoles: [
    { uiId: 'role-initial', key: 'outcome', label: '结果变量', role: 'outcome', level: 1, acceptedTypes: 'continuous', structureRole: '' },
  ],
  constructs: [],
  robustnessAnalyses: [],
  effectSize: 0.15,
  alpha: 0.05,
  targetPower: 0.8,
  predictors: 3,
  groups: 2,
  solveFor: 'sample_size',
}

export function roleKey(role: PlannedRoleDraft, index: number): string {
  return role.key.trim() || `role_${index + 1}`
}

export function fromPlan(plan: StudyPlanVersion): PlanDraft {
  const primary = plan.analysisDeclarations.find(analysis => analysis.role === 'primary')
  const power = plan.powerPlan as Record<string, unknown> | null | undefined
  const effect = power?.effectSize
  const effectValue = effect && typeof effect === 'object' && 'value' in effect ? Number(effect.value) : EMPTY_DRAFT.effectSize
  return {
    title: plan.title,
    researchQuestion: plan.researchQuestion,
    hypothesis: plan.hypotheses[0]?.label ?? EMPTY_DRAFT.hypothesis,
    estimand: plan.estimands[0]?.quantity ?? EMPTY_DRAFT.estimand,
    missingDataStrategy: plan.missingDataPlan.strategy,
    sliceId: primary?.capabilitySliceId ?? EMPTY_DRAFT.sliceId,
    plannedRoles: (plan.sampleDefinition.roles ?? []).map((role, index) => {
      const item = role as Record<string, unknown>
      return {
        uiId: nextDraftItemId('role'),
        key: String(item.key ?? item.id ?? item.role ?? `role_${index + 1}`),
        label: String(item.label ?? item.role ?? `角色 ${index + 1}`),
        role: String(item.role ?? item.key ?? 'outcome'),
        level: Number(item.level ?? 1),
        acceptedTypes: Array.isArray(item.acceptedTypes) ? item.acceptedTypes.join(', ') : '',
        structureRole: String(item.structureRole ?? ''),
      }
    }),
    constructs: (plan.measurementPlan.constructs ?? []).map((construct, index) => {
      const item = construct as Record<string, unknown>
      return {
        uiId: nextDraftItemId('construct'),
        id: String(item.id ?? `construct_${index + 1}`),
        label: String(item.label ?? `构念 ${index + 1}`),
        itemIds: Array.isArray(item.itemIds) ? item.itemIds.join(', ') : '',
      }
    }),
    robustnessAnalyses: plan.analysisDeclarations.filter(analysis => analysis.role === 'robustness').map((analysis) => {
      const item = analysis as Record<string, unknown>
      const parameters = item.parameters as Record<string, unknown> | undefined
      return { uiId: nextDraftItemId('robustness'), sliceId: String(item.capabilitySliceId ?? ''), rationale: String(parameters?.rationale ?? '') }
    }),
    effectSize: Number.isFinite(effectValue) ? effectValue : EMPTY_DRAFT.effectSize,
    alpha: typeof power?.alpha === 'number' ? power.alpha : EMPTY_DRAFT.alpha,
    targetPower: typeof power?.targetPower === 'number' ? power.targetPower : EMPTY_DRAFT.targetPower,
    predictors: typeof power?.predictors === 'number' ? power.predictors : EMPTY_DRAFT.predictors,
    groups: typeof power?.groups === 'number' ? power.groups : EMPTY_DRAFT.groups,
    solveFor: power?.solveFor === 'power' || power?.solveFor === 'effect_size' ? power.solveFor : 'sample_size',
  }
}

export function toPayload(draft: PlanDraft, context: StudyContext, projectId: string): Record<string, unknown> {
  const primaryFamily = draft.sliceId.split('.', 1)[0]
  const plannedRoles = draft.plannedRoles
    .map((role, index) => ({
      key: roleKey(role, index),
      label: role.label.trim() || roleKey(role, index),
      role: role.role.trim() || roleKey(role, index),
      level: Math.max(1, Math.round(role.level || 1)),
      ...(role.acceptedTypes.trim()
        ? { acceptedTypes: role.acceptedTypes.split(',').map(value => value.trim()).filter(Boolean) }
        : {}),
      ...(role.structureRole.trim() ? { structureRole: role.structureRole.trim() } : {}),
    }))
  const constructs = draft.constructs
    .filter(construct => construct.id.trim() || construct.label.trim() || construct.itemIds.trim())
    .map((construct, index) => ({
      id: construct.id.trim() || `construct_${index + 1}`,
      label: construct.label.trim() || `构念 ${index + 1}`,
      itemIds: construct.itemIds.split(',').map(value => value.trim()).filter(Boolean),
    }))
  const robustnessAnalyses = draft.robustnessAnalyses
    .filter(analysis => analysis.sliceId.trim())
    .map((analysis, index) => ({
      id: `analysis_robustness_${index + 1}`,
      role: 'robustness',
      estimandIds: ['estimand_primary'],
      capabilitySliceId: analysis.sliceId.trim(),
      requestedMethod: analysis.sliceId.split('.', 1)[0],
      parameters: { rationale: analysis.rationale.trim() },
    }))
  const robustnessAnalysisIds = robustnessAnalyses.map(analysis => analysis.id)
  const payload: Record<string, unknown> = {
    schemaVersion: '2.0.0',
    title: draft.title.trim(),
    researchQuestion: draft.researchQuestion.trim(),
    hypotheses: draft.hypothesis.trim() ? [{
      id: 'hypothesis_primary',
      label: draft.hypothesis.trim(),
      analysisRole: 'primary',
      declarationTiming: 'unspecified',
      direction: 'two_sided',
      estimandIds: ['estimand_primary'],
    }] : [],
    estimands: [{
      id: 'estimand_primary',
      quantity: draft.estimand.trim(),
      outcomeScale: 'original',
      population: 'analysis_sample',
      contrast: null,
      conditioning: null,
      causalTarget: false,
    }],
    analysisDeclarations: [{
      id: 'analysis_primary',
      role: 'primary',
      estimandIds: ['estimand_primary'],
      capabilitySliceId: draft.sliceId,
      requestedMethod: primaryFamily,
      robustnessAnalysisIds,
      parameters: {},
    }, ...robustnessAnalyses],
    multiplicityFamilies: [],
    sampleDefinition: { roles: plannedRoles },
    measurementPlan: { constructs },
    missingDataPlan: { strategy: draft.missingDataStrategy.trim(), sensitivityAnalysisIds: [], reportMissingness: true },
    context,
    powerPlan: null,
  }
  if (primaryFamily === 'power_analysis') {
    const designFamily = draft.sliceId.split('.').at(-1) ?? 'regression'
    const metric = designFamily === 't_test' ? 'cohens_d' : designFamily === 'factorial_anova' ? 'cohens_f' : 'cohens_f2'
    payload.powerPlan = {
      schemaVersion: '0.1.0',
      analysisId: `plan-power-${projectId.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 40)}`,
      name: `${draft.title.trim() || 'StudyPlan'} 功效规格`,
      family: 'power_analysis',
      designFamily,
      method: 'analytic',
      solveFor: draft.solveFor,
      alpha: draft.alpha,
      targetPower: draft.targetPower,
      effectSize: draft.solveFor === 'effect_size' ? null : { metric, value: draft.effectSize },
      effectSizeMetric: draft.solveFor === 'effect_size' ? metric : null,
      predictors: Math.max(1, Math.round(draft.predictors)),
      groups: Math.max(1, Math.round(draft.groups)),
      simulations: 5000,
      alternative: 'two_sided',
      roundingRule: 'ceil',
    }
  }
  return payload
}
