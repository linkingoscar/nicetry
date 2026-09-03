import type { ApplicableCapability } from '../types/analysis-context'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { methodDefinitions, type MethodDefinition, type MethodVisibilityTier } from './methodDefinitions'

export interface MethodLibraryDefinition extends MethodDefinition {
  libraryId: string
  procedure?: EmpiricalProcedure
  processModelNumber?: 1 | 4
}

interface ProcedurePreset {
  id: string
  label: string
  aliases: string[]
  description: string
  keywords: string[]
  procedure: EmpiricalProcedure
}

interface ModelPreset {
  id: string
  label: string
  aliases: string[]
  description: string
  keywords: string[]
  processModelNumber?: 1 | 4
  advanced?: boolean
  visibilityTier?: MethodVisibilityTier
}

interface MethodCopyOverride {
  label?: string
  description?: string
  aliases?: string[]
  keywords?: string[]
}

const COMMON_FORM_METHOD_IDS = new Set([
  'experiment.factorial-anova',
  'experiment.ancova',
  'experiment.repeated-measures',
  'experiment.mixed-design',
  'multilevel.aggregation',
  'multilevel.gaussian-lmm',
])

const METHOD_COPY_OVERRIDES: Record<string, MethodCopyOverride> = {
  'measurement.ordinal-reliability': {
    label: '高级序数信度（Polychoric α / ω）',
    description: '使用高级有序题项规格估计序数 α / ω；基础“信度与项目分析”仍是常用默认入口。',
    aliases: ['advanced reliability', 'polychoric reliability'],
    keywords: ['高级测量', 'polychoric'],
  },
  'measurement.polychoric-efa': {
    label: '高级 EFA（Polychoric / MAP）',
    description: '显式配置 polychoric 相关、MAP / 因子保留与高级旋转；基础 EFA 保留为常用入口。',
    aliases: ['advanced EFA'],
    keywords: ['高级测量', 'polychoric', 'MAP'],
  },
  'measurement.cfa': {
    label: '高级 CFA（ML / MLR / WLSMV）',
    description: '显式控制指标、估计器和确认性测量边界；基础 CFA 保留为常用默认入口。',
    aliases: ['advanced CFA'],
    keywords: ['高级测量', 'MLR', 'WLSMV'],
  },
  'measurement.invariance': {
    label: '高级多组测量等值性',
    description: '用于更完整的多组等值规格和高级约束；基础等值性检查保留为常用入口。',
    aliases: ['advanced measurement invariance'],
    keywords: ['高级测量', '多组约束'],
  },
  'measurement.common-method-bias': {
    label: '高级共同方法偏差（Marker / ULMC）',
    description: '显式配置 Marker / ULMC 敏感性规格；基础共同方法诊断保留为常用入口。',
    aliases: ['advanced CMB'],
    keywords: ['高级测量', 'Marker', 'ULMC'],
  },
  'measurement.esem-bifactor-irt': {
    label: 'ESEM / Bifactor / IRT / DIF（高级）',
  },
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

const MODEL_PRESETS: Record<string, ModelPreset[]> = {
  'model.process': [
    {
      id: 'simple-mediation',
      label: '简单中介（PROCESS Model 4）',
      aliases: ['simple mediation', 'Model 4', '中介效应', '间接效应'],
      description: '用 X、M、Y 表单配置简单中介模型，再进入现有模型草稿复核与运行。',
      keywords: ['中介', 'Model 4', 'bootstrap', '间接效应'],
      processModelNumber: 4,
      advanced: false,
      visibilityTier: 'common',
    },
    {
      id: 'simple-moderation',
      label: '简单调节（PROCESS Model 1）',
      aliases: ['simple moderation', 'Model 1', '调节效应', 'interaction'],
      description: '用 X、W、Y 表单配置简单调节模型，并可显式设置中心化和 bootstrap。',
      keywords: ['调节', 'Model 1', '交互项', '中心化'],
      processModelNumber: 1,
      advanced: false,
      visibilityTier: 'common',
    },
    {
      id: 'full-catalog',
      label: 'PROCESS 完整模型库（高级）',
      aliases: ['PROCESS catalog', 'PROCESS 55 models', '条件过程模型'],
      description: '进入完整 PROCESS 模型目录、画布与高级路径编辑。',
      keywords: ['PROCESS', '条件过程', '高级模型', '完整模型库'],
      advanced: true,
      visibilityTier: 'advanced',
    },
  ],
}

export function methodsForCapability(sliceId: string): MethodDefinition[] {
  return methodDefinitions.filter((method) => method.capabilitySliceIds.includes(sliceId))
}

export function expandMethodForLibrary(method: MethodDefinition): MethodLibraryDefinition[] {
  const procedurePresets = PROCEDURE_PRESETS[method.id]
  if (procedurePresets) {
    return procedurePresets.map((preset) => ({
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

  const modelPresets = MODEL_PRESETS[method.id]
  if (modelPresets) {
    return modelPresets.map((preset) => ({
      ...method,
      id: `${method.id}.${preset.id}`,
      libraryId: `${method.id}.${preset.id}`,
      label: preset.label,
      aliases: [...new Set([...method.aliases, ...preset.aliases])],
      description: preset.description,
      keywords: [...new Set([...method.keywords, ...preset.keywords])],
      processModelNumber: preset.processModelNumber,
      advanced: preset.advanced ?? method.advanced,
      visibilityTier: preset.visibilityTier ?? method.visibilityTier,
    }))
  }

  const commonForm = COMMON_FORM_METHOD_IDS.has(method.id)
  const copyOverride = METHOD_COPY_OVERRIDES[method.id]
  return [{
    ...method,
    libraryId: method.id,
    label: copyOverride?.label ?? method.label,
    description: copyOverride?.description ?? method.description,
    aliases: copyOverride?.aliases ? [...new Set([...method.aliases, ...copyOverride.aliases])] : method.aliases,
    keywords: copyOverride?.keywords ? [...new Set([...method.keywords, ...copyOverride.keywords])] : method.keywords,
    advanced: commonForm ? false : method.advanced,
    visibilityTier: commonForm ? 'common' : method.visibilityTier,
  }]
}

export function libraryMethodsForCapability(capability: ApplicableCapability): MethodLibraryDefinition[] {
  return methodsForCapability(capability.sliceId).flatMap(expandMethodForLibrary)
}
