import type { AnalysisParadigm } from '../../types/study-context'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'

interface CandidateLike {
  id: string
  label: string
}

export function methodLabel(value: EmpiricalConfigValue): string {
  if (value.factorCountMethod === 'parallel_analysis') return '平行分析'
  if (value.factorCountMethod === 'manual') return `手动 ${value.factorCount} 因子`
  return 'Kaiser 因子保留'
}

interface EmpiricalPlanItemInput {
  value: EmpiricalConfigValue
  researchParadigm: AnalysisParadigm
  nestedContext: boolean
  group?: CandidateLike
  aggregation?: CandidateLike
  outcome?: CandidateLike
}

export function buildEmpiricalPlanItems({
  value,
  researchParadigm,
  nestedContext,
  group,
  aggregation,
  outcome,
}: EmpiricalPlanItemInput): string[] {
  const showCrossSectional = researchParadigm === 'questionnaire'
  const crossSectionalPlanItems = [
    value.correlationMethod === 'pearson' ? 'Pearson 相关' : value.correlationMethod === 'spearman' ? 'Spearman 相关' : '偏相关',
    methodLabel(value),
    nestedContext ? '组间比较已转交 cluster-aware 流程' : group ? `按 ${group.label} 分组` : '不做组间比较',
    aggregation ? `按 ${aggregation.label} 运行聚合诊断` : '不做 cluster 聚合诊断',
    nestedContext
      ? '普通分层回归已阻断'
      : outcome
      ? `回归：${outcome.label} ← ${value.predictorVariableIds.length} 个预测 + ${value.controlVariableIds.length} 个控制`
      : '不做分层回归',
    value.responseSurfacePredictorIds.length === 2 ? '包含响应面' : '不做响应面',
  ]
  const repeatedMeasurementPlanItems = [
    '按个体与时间结构建模',
    '逐行横截面推断已关闭',
    value.longitudinalPanel
      ? `${value.longitudinalPanel.measurementMode === 'latent_items' ? '潜变量 ' : ''}${value.longitudinalPanel.modelType === 'ri_clpm' ? 'RI-CLPM' : value.longitudinalPanel.modelType === 'lcm_sr' ? 'LCM-SR' : 'CLPM'} · ${value.longitudinalPanel.waves.length} 波`
      : value.diaryMultilevel
        ? `${value.diaryMultilevel.analysisType === 'mediation' ? '多层中介' : value.diaryMultilevel.analysisType.toUpperCase()}`
        : '尚未启用重复测量模型',
  ]
  return showCrossSectional ? crossSectionalPlanItems : repeatedMeasurementPlanItems
}
