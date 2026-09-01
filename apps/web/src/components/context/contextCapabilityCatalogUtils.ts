import type { ApplicableCapability } from '../../types/analysis-context'
import type { DatasetVariable } from '../../types/datasets'
import type { AdvancedAnalysisCapability, CapabilityMaturity, PublicationEligibility } from '../../types/advanced'
import type { WorkbenchTarget } from './workbenchNavigation'

export function familyLabel(family: string): string {
  const labels: Record<string, string> = {
    empirical: '基础统计与实证',
    model: '路径与结构方程',
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
  return variables.map((variable) => ({
    id: variable.id,
    name: variable.originalName,
    label: variable.label,
    type: variable.confirmedType === 'continuous'
      ? 'numeric' as const
      : variable.confirmedType === 'binary' || variable.confirmedType === 'nominal' || variable.confirmedType === 'ordinal' || variable.confirmedType === 'likert'
        ? 'categorical' as const
        : variable.confirmedType === 'text'
          ? 'text' as const
          : 'text' as const,
    missingRate: variable.missingRate,
    levels: Object.keys(variable.valueLabels ?? {}),
  }))
}

export function wizardCapability(capability: ApplicableCapability): AdvancedAnalysisCapability {
  return {
    family: capability.family as AdvancedAnalysisCapability['family'],
    sliceId: capability.sliceId,
    label: capability.label,
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

export function internalWorkbenchTarget(capability: ApplicableCapability): WorkbenchTarget | null {
  if (!capability.executionAvailable) return null
  const method = { sliceId: capability.sliceId, label: capability.label }
  if (capability.family === 'model') return { view: 'model', ...method }
  if (capability.sliceId.startsWith('empirical.panel.')) return { view: 'empirical', tab: 'longitudinal', ...method }
  if (capability.sliceId.startsWith('empirical.diary.')) return { view: 'empirical', tab: 'diary', ...method }
  const tabs = {
    'empirical.cross_sectional.overview': 'overview',
    'empirical.cross_sectional.measurement': 'measurement',
    'empirical.cross_sectional.group_comparison': 'groups',
    'empirical.cross_sectional.hierarchical_regression': 'regression',
    'empirical.cross_sectional.response_surface': 'advanced',
  } as const
  const tab = tabs[capability.sliceId as keyof typeof tabs]
  return tab ? { view: 'empirical', tab, ...method } : null
}
