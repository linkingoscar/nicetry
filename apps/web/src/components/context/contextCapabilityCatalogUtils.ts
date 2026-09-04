import { methodForCapability, type MethodDefinition } from '../../methods/methodDefinitions'
import type { MethodLibraryDefinition } from '../../methods/methodLibraryPresets'
import type { ApplicableCapability } from '../../types/analysis-context'
import type { DatasetVariable } from '../../types/datasets'
import type { AdvancedAnalysisCapability, CapabilityMaturity, PublicationEligibility } from '../../types/advanced'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { WorkbenchTarget } from './workbenchNavigation'

export function familyLabel(family: string): string {
  const labels: Record<string, string> = {
    empirical: '基础统计与实证',
    model: '中介、调节与结构方程',
    questionnaire_measurement: '问卷与测量',
    experimental_design: '实验与组间比较',
    multilevel_model: '多层与嵌套模型',
    multiple_imputation: '缺失数据与插补',
    power_analysis: '功效与样本量',
  }
  return labels[family] ?? family.replaceAll('_', ' ')
}

export function maturityLabel(maturity: CapabilityMaturity): string {
  if (maturity === 'publication_ready') return '论文级就绪'
  if (maturity === 'reviewer_ready') return '审稿就绪候选'
  return maturity === 'validated' ? '已验证' : '实验性'
}

export function publicationLabel(eligibility: PublicationEligibility): string {
  if (eligibility === 'eligible') return '可作为论文级主分析'
  return eligibility === 'conditional' ? '有条件：仍需论文证据图' : '暂不具备论文主分析资格'
}

export function toWizardVariables(variables: DatasetVariable[]) {
  return variables.map((variable) => {
    const effectiveType = variable.confirmedType ?? variable.inferredType
    return {
      id: variable.id,
      name: variable.originalName,
      label: variable.label,
      type: effectiveType === 'continuous'
        ? 'numeric' as const
        : effectiveType === 'binary' || effectiveType === 'nominal' || effectiveType === 'ordinal' || effectiveType === 'likert'
          ? 'categorical' as const
          : 'text' as const,
      missingRate: variable.missingRate,
      levels: Object.keys(variable.valueLabels ?? {}),
    }
  })
}

export function wizardCapability(capability: ApplicableCapability): AdvancedAnalysisCapability {
  const method = methodForCapability(capability.sliceId)
  return {
    family: capability.family as AdvancedAnalysisCapability['family'],
    sliceId: capability.sliceId,
    label: method?.label ?? capability.label,
    status: capability.status === 'supported' ? 'supported' : 'experimental',
    specVersion: '0.1.0',
    resultVersion: '0.1.0',
    plannedEngine: 'R',
    minimumValidation: capability.missingRequirements,
    executionAvailable: capability.executionAvailable,
    slices: [],
    maturityLevel: capability.maturityLevel,
    publicationEligibility: capability.publicationEligibility,
    publicationEligibilityReason: capability.publicationEligibilityReason,
  }
}

function isMethodLibraryDefinition(
  definition: MethodLibraryDefinition | MethodDefinition,
): definition is MethodLibraryDefinition {
  return 'libraryId' in definition
}

function defaultProcedureForAdapter(adapter: MethodDefinition['adapter']): EmpiricalProcedure | undefined {
  if (adapter === 'empirical-longitudinal') return 'longitudinal'
  if (adapter === 'empirical-diary') return 'diary'
  if (adapter === 'empirical-overview') return 'descriptives'
  if (adapter === 'empirical-measurement') return 'reliability'
  if (adapter === 'empirical-groups') return 'groups'
  if (adapter === 'empirical-regression') return 'regression'
  if (adapter === 'empirical-advanced') return 'response_surface'
  return undefined
}

export function internalWorkbenchTarget(
  capability: ApplicableCapability,
  definitionOverride?: MethodLibraryDefinition | MethodDefinition,
): WorkbenchTarget | null {
  if (!capability.executionAvailable) return null
  const definition = definitionOverride ?? methodForCapability(capability.sliceId)
  if (!definition || definition.adapter === 'advanced-wizard') return null

  const method: Pick<WorkbenchTarget, 'sliceId' | 'methodId' | 'label' | 'procedure' | 'processModelNumber' | 'processMediatorCount'> = {
    sliceId: capability.sliceId,
    methodId: isMethodLibraryDefinition(definition) ? definition.libraryId : definition.id,
    label: definition.label,
  }
  if (isMethodLibraryDefinition(definition)) {
    if (definition.procedure) method.procedure = definition.procedure
    if (definition.processModelNumber) method.processModelNumber = definition.processModelNumber
    if (definition.processMediatorCount) method.processMediatorCount = definition.processMediatorCount
  }
  method.procedure ??= defaultProcedureForAdapter(definition.adapter)

  if (definition.adapter === 'model') return { view: 'model', ...method }
  if (definition.adapter === 'empirical-longitudinal') return { view: 'empirical', tab: 'longitudinal', ...method }
  if (definition.adapter === 'empirical-diary') return { view: 'empirical', tab: 'diary', ...method }
  if (definition.adapter === 'empirical-overview') return { view: 'empirical', tab: 'overview', ...method }
  if (definition.adapter === 'empirical-measurement') return { view: 'empirical', tab: 'measurement', ...method }
  if (definition.adapter === 'empirical-groups') return { view: 'empirical', tab: 'groups', ...method }
  if (definition.adapter === 'empirical-regression') return { view: 'empirical', tab: 'regression', ...method }
  if (definition.adapter === 'empirical-advanced') return { view: 'empirical', tab: 'advanced', ...method }
  return null
}
