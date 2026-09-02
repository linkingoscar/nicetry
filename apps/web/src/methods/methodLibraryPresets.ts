import type { ApplicableCapability } from '../types/analysis-context'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { methodDefinitions, type MethodDefinition } from './methodDefinitions'

export interface MethodLibraryDefinition extends MethodDefinition {
  libraryId: string
  procedure?: EmpiricalProcedure
}

interface ProcedurePreset {
  id: string
  label: string
  aliases: string[]
  description: string
  keywords: string[]
  procedure: EmpiricalProcedure
}

const PROCEDURE_PRESETS: Record<string, ProcedurePreset[]> = {
  'empirical.overview': [
    {
      id: 'descriptives',
      label: '描述统计',
      aliases: ['descriptives', '描述性统计', '均值', '标准差'],
      description: '查看所选变量的样本量、位置、离散与分布统计。',
      keywords: ['描述', '均值', '标准差', '分布'],
      procedure: 'descriptives',
    },
    {
      id: 'frequencies',
      label: '频数分析',
      aliases: ['frequencies', '频率', '频数表'],
      description: '查看分类或有序变量的频数、百分比与缺失摘要。',
      keywords: ['频数', '百分比', '分类变量'],
      procedure: 'frequencies',
    },
    {
      id: 'missing',
      label: '缺失数据诊断',
      aliases: ['missing data', '缺失诊断', '完整案例'],
      description: '检查所选变量的缺失率、缺失模式与完整案例损失。',
      keywords: ['缺失', '完整案例', '样本流'],
      procedure: 'missing',
    },
    {
      id: 'correlation',
      label: '相关与偏相关',
      aliases: ['correlation', 'Pearson', 'Spearman', '偏相关'],
      description: '计算相关或偏相关，并保留置信区间和多重比较信息。',
      keywords: ['相关', 'Pearson', 'Spearman', '偏相关'],
      procedure: 'correlation',
    },
  ],
  'empirical.measurement': [
    {
      id: 'reliability',
      label: '信度与项目分析',
      aliases: ['reliability', 'Cronbach alpha', 'omega', '信度'],
      description: '对已保存量表或临时题项组运行信度与项目诊断。',
      keywords: ['信度', 'alpha', 'omega', '项目分析'],
      procedure: 'reliability',
    },
    {
      id: 'efa',
      label: '探索性因子分析（EFA）',
      aliases: ['EFA', 'exploratory factor analysis', '探索性因子'],
      description: '对题项组执行当前实证路径支持的探索性因子分析。',
      keywords: ['EFA', '因子分析', '载荷', '旋转'],
      procedure: 'efa',
    },
    {
      id: 'cfa',
      label: '验证性因子分析（CFA）',
      aliases: ['CFA', 'confirmatory factor analysis', '验证性因子'],
      description: '对已定义构念执行当前基础实证路径支持的 CFA。',
      keywords: ['CFA', '拟合', '载荷', '测量模型'],
      procedure: 'cfa',
    },
    {
      id: 'validity',
      label: '收敛与区分效度',
      aliases: ['validity', 'AVE', 'HTMT', 'Fornell Larcker'],
      description: '基于兼容测量模型计算当前支持的收敛与区分效度指标。',
      keywords: ['效度', 'AVE', 'HTMT', 'CR'],
      procedure: 'validity',
    },
    {
      id: 'common-method',
      label: '共同方法偏差诊断',
      aliases: ['common method bias', 'CMB', 'Harman'],
      description: '运行当前基础实证路径支持的共同方法偏差诊断。',
      keywords: ['共同方法', 'Harman', 'CMB'],
      procedure: 'common_method',
    },
    {
      id: 'invariance',
      label: '多组测量等值性',
      aliases: ['measurement invariance', '等值性', '多组 CFA'],
      description: '按当前基础实证路径检查多组测量等值性。',
      keywords: ['等值性', '多组', 'CFA'],
      procedure: 'invariance',
    },
  ],
  'empirical.hierarchical-regression': [
    {
      id: 'regression',
      label: '线性 / 分层回归',
      aliases: ['regression', 'hierarchical regression', 'OLS', '分层回归'],
      description: '按区块配置控制变量与核心预测变量并运行线性回归。',
      keywords: ['回归', 'OLS', 'R2', '区块'],
      procedure: 'regression',
    },
    {
      id: 'relative-importance',
      label: '相对重要性分析',
      aliases: ['relative importance', '相对贡献', '重要性分析'],
      description: '基于明确的回归模型估计当前支持的预测变量相对贡献。',
      keywords: ['回归', '相对重要性', '贡献'],
      procedure: 'relative_importance',
    },
  ],
}

export function methodsForCapability(sliceId: string): MethodDefinition[] {
  return methodDefinitions.filter((method) => method.capabilitySliceIds.includes(sliceId))
}

export function expandMethodForLibrary(method: MethodDefinition): MethodLibraryDefinition[] {
  const presets = PROCEDURE_PRESETS[method.id]
  if (!presets) return [{ ...method, libraryId: method.id }]

  return presets.map((preset) => ({
    ...method,
    id: `${method.id}.${preset.id}`,
    libraryId: `${method.id}.${preset.id}`,
    label: preset.label,
    aliases: [...new Set([...method.aliases, ...preset.aliases])],
    description: preset.description,
    keywords: [...new Set([...method.keywords, ...preset.keywords])],
    procedure: preset.procedure,
  }))
}

export function libraryMethodsForCapability(capability: ApplicableCapability): MethodLibraryDefinition[] {
  return methodsForCapability(capability.sliceId).flatMap(expandMethodForLibrary)
}
