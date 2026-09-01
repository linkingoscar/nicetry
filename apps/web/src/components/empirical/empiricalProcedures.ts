import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { ApplicableCapability } from '../../types/analysis-context'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'

export interface ProcedureDefinition {
  id: EmpiricalProcedure
  label: string
  family: string
  tab: EmpiricalResultTab
  slice: string
  hint: string
}
const overview = 'empirical.cross_sectional.overview'
const measurement = 'empirical.cross_sectional.measurement'
export const empiricalProcedures: ProcedureDefinition[] = [
  { id: 'descriptives', label: '描述统计', family: '描述与数据检查', tab: 'overview', slice: overview, hint: '选择数值变量，查看均值、标准差、范围与分布。' },
  { id: 'frequencies', label: '频数分析', family: '描述与数据检查', tab: 'overview', slice: overview, hint: '选择变量，查看各取值的频数和比例。' },
  { id: 'missing', label: '缺失数据诊断', family: '描述与数据检查', tab: 'overview', slice: overview, hint: '只检查所选变量的缺失率、模式与完整案例损失，不自动插补。' },
  { id: 'correlation', label: '相关分析', family: '关系与比较', tab: 'correlation', slice: overview, hint: '选择至少两个变量；偏相关需要另外指定控制变量。' },
  { id: 'groups', label: '组间差异检验', family: '关系与比较', tab: 'groups', slice: 'empirical.cross_sectional.group_comparison', hint: '指定检验变量和分组变量；两组与多组按已有检验规则执行，不自动运行测量等值性。' },
  { id: 'reliability', label: '信度与项目分析', family: '量表与测量', tab: 'measurement', slice: measurement, hint: '选择量表，在本次样本上重新计算标准化 α、ω 和项目诊断；ω 使用单因子 minres。' },
  { id: 'efa', label: '探索性因子分析（EFA）', family: '量表与测量', tab: 'measurement', slice: measurement, hint: '选择题项所属量表，设置因子保留与旋转；包含 KMO/Bartlett，不运行 CFA。' },
  { id: 'cfa', label: '验证性因子分析（CFA）', family: '量表与测量', tab: 'measurement', slice: measurement, hint: '按已确认的构念–题项结构拟合；连续题项 MLR、有序题项 WLSMV。' },
  { id: 'validity', label: '收敛与区分效度', family: '量表与测量', tab: 'measurement', slice: measurement, hint: 'CR/AVE、Fornell–Larcker、HTMT；本方法依赖 CFA，会明确运行该模型，不运行 EFA。' },
  { id: 'common_method', label: '共同方法偏差诊断', family: '量表与测量', tab: 'measurement', slice: measurement, hint: 'Harman 与 ULMC 敏感性诊断，不能据此单独排除共同方法偏差。' },
  { id: 'invariance', label: '多组测量等值性', family: '量表与测量', tab: 'measurement', slice: measurement, hint: '声明分组变量和构念结构，仅执行多组测量等值性模型。' },
  { id: 'aggregation', label: 'ICC 与聚合诊断', family: '聚类与多层', tab: 'groups', slice: 'multilevel_model.aggregation.icc_rwg', hint: '指定 cluster 与构念，检查 ICC(1)、ICC(2)、设计效应和 rwg。' },
  { id: 'regression', label: '分层线性回归', family: '回归模型', tab: 'regression', slice: 'empirical.cross_sectional.hierarchical_regression', hint: '指定因变量、预测变量与控制区块；报告 OLS 及 HC3 敏感性诊断。' },
  { id: 'relative_importance', label: '相对重要性分析', family: '回归模型', tab: 'advanced', slice: 'empirical.cross_sectional.hierarchical_regression', hint: '声明因变量、预测与控制变量；以 OLS 模型为必要依赖，计算预测变量的相对贡献。' },
  { id: 'response_surface', label: '多项式回归与响应面', family: '回归模型', tab: 'advanced', slice: 'empirical.cross_sectional.response_surface', hint: '指定因变量和两个焦点预测变量，拟合多项式模型与一致/不一致线。' },
  { id: 'longitudinal', label: '纵向面板模型', family: '纵向与动态模型', tab: 'longitudinal', slice: 'empirical.panel.', hint: '参照 Mplus 的变量、模型、估计与输出分层设置，选择 CLPM、RI-CLPM 或 LCM-SR。' },
  { id: 'diary', label: '日记 / ESM 模型', family: '纵向与动态模型', tab: 'diary', slice: 'empirical.diary.', hint: '指定个体、时间、层级与模型类型；可选择 LMM、GLMM、多层中介或 DSEM。' },
]

export function procedureDefinition(id: EmpiricalProcedure) {
  const definition = empiricalProcedures.find((item) => item.id === id)
  if (!definition) throw new Error(`未知的分析方法: ${id}`)
  return definition
}

export function availableProcedures(capabilities: ApplicableCapability[], paradigm: string, nested: boolean) {
  return empiricalProcedures.filter((item) => {
    if (item.id === 'longitudinal' && paradigm !== 'longitudinal') return false
    if (item.id === 'diary' && paradigm !== 'diary') return false
    if (['groups', 'regression', 'relative_importance', 'response_surface', 'invariance'].includes(item.id) && (nested || paradigm !== 'questionnaire')) return false
    return capabilities.some((c) => c.executionAvailable && c.applicable && c.productVisible &&
      (item.slice.endsWith('.') ? c.sliceId.startsWith(item.slice) : c.sliceId === item.slice))
  })
}

export function procedureReadiness(value: EmpiricalConfigValue): string | null {
  const p = value.procedure
  if (['descriptives', 'frequencies', 'missing', 'correlation', 'groups'].includes(p)) {
    if (value.analysisVariableIds.length < (p === 'correlation' ? 2 : 1)) return '请选择分析变量；相关分析至少需要两个变量。'
  }
  if (['reliability', 'efa', 'cfa', 'validity', 'common_method', 'invariance', 'aggregation'].includes(p) && !value.constructIds.length) return '请选择本次分析的量表。'
  if (['groups', 'invariance'].includes(p) && !value.groupVariableId) return '请选择分组变量。'
  if (p === 'aggregation' && !value.aggregationVariableId) return '请选择 cluster 聚合变量。'
  if (['regression', 'relative_importance', 'response_surface'].includes(p) && !value.outcomeVariableId) return '请选择因变量。'
  if (['regression', 'relative_importance'].includes(p) && !value.predictorVariableIds.length) return '请选择预测变量。'
  if (p === 'response_surface' && value.responseSurfacePredictorIds.length !== 2) return '请选择两个不同的焦点预测变量。'
  if (p === 'correlation' && value.correlationMethod === 'partial' && !value.controlVariableIds.length) return '偏相关需要选择控制变量。'
  if (p === 'longitudinal' && !value.longitudinalPanel) return '请启用并配置纵向面板模型。'
  if (p === 'diary' && !value.diaryMultilevel) return '请启用并配置日记 / ESM 模型。'
  return null
}
