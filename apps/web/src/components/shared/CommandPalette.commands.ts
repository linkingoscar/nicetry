import type { EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'

export interface CommandItem {
  id: string
  category: 'workspace' | 'empirical_tab' | 'action' | 'variable'
  title: string
  subtitle?: string
  icon: string
  action: () => void
}

interface BuildCommandPaletteCommandsOptions {
  onSelectView: (view: 'data' | 'empirical' | 'model' | 'methods') => void
  onSelectEmpiricalTab?: (tab: EmpiricalResultTab) => void
  onLoadDemo?: () => void
  variables?: Array<{ id: string; label: string }>
  onClose: () => void
}

export function buildCommandPaletteCommands({
  onSelectView,
  onSelectEmpiricalTab,
  onLoadDemo,
  variables = [],
  onClose,
}: BuildCommandPaletteCommandsOptions): CommandItem[] {
  const list: CommandItem[] = [
    {
      id: 'view_data',
      category: 'workspace',
      title: '跳转: 数据与测量 (Ctrl+1)',
      subtitle: '导入问卷数据、数据质量筛查与构念测量计分',
      icon: '📁',
      action: () => {
        onSelectView('data')
        onClose()
      },
    },
    {
      id: 'view_empirical',
      category: 'workspace',
      title: '跳转: 问卷实证分析 (Ctrl+2)',
      subtitle: '描述正态、相关矩阵、EFA/CFA 信效度与实证管道',
      icon: '📊',
      action: () => {
        onSelectView('empirical')
        onClose()
      },
    },
    {
      id: 'view_model',
      category: 'workspace',
      title: '跳转: 模型画布 PROCESS & SEM (Ctrl+3)',
      subtitle: 'PROCESS 经典模型与高阶 SEM / 多群组工作室画板',
      icon: '🧩',
      action: () => {
        onSelectView('model')
        onClose()
      },
    },
    {
      id: 'action_higher_order_sem',
      category: 'action',
      title: '高阶 SEM: 创建二阶潜变量 (Higher-Order Latent)',
      subtitle: '归纳 3+ 个一阶因子构建高阶潜结构模型',
      icon: '🧬',
      action: () => {
        onSelectView('model')
        onClose()
      },
    },
    {
      id: 'action_multi_group_sem',
      category: 'action',
      title: '多群组 SEM: 测量等值性检验工作室 (MGA Studio)',
      subtitle: '配置 2–5 组 5 阶段等值性检验与部分等值释放',
      icon: '👥',
      action: () => {
        onSelectView('model')
        onClose()
      },
    },
    {
      id: 'action_longitudinal_swimlane',
      category: 'empirical_tab',
      title: '实证分区: 7. 纵向面板',
      subtitle: 'CLPM、RI-CLPM、LCM-SR与纵向测量等值性真实结果',
      icon: '🌊',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('longitudinal')
        onClose()
      },
    },
    {
      id: 'view_methods',
      category: 'workspace',
      title: '跳转: 当前数据的专属方法 (Ctrl+4)',
      subtitle: '按研究上下文开放缺失处理、实验分析和测量扩展',
      icon: '🧪',
      action: () => {
        onSelectView('methods')
        onClose()
      },
    },
    {
      id: 'tab_diary',
      category: 'empirical_tab',
      title: '实证分区: 8. 日记 / ESM',
      subtitle: 'LMM、GLMM、多层中介与Bayesian DSEM真实结果',
      icon: '🗓️',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('diary')
        onClose()
      },
    },
    {
      id: 'tab_overview',
      category: 'empirical_tab',
      title: '实证分区: 1. 描述与正态性',
      subtitle: '样本描述、缺失值诊断与偏度/峰度正态性检验',
      icon: '📈',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('overview')
        onClose()
      },
    },
    {
      id: 'tab_correlation',
      category: 'empirical_tab',
      title: '实证分区: 2. 相关与矩阵',
      subtitle: 'Pearson / Spearman 相关矩阵与控制变量偏相关',
      icon: '🔗',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('correlation')
        onClose()
      },
    },
    {
      id: 'tab_measurement',
      category: 'empirical_tab',
      title: '实证分区: 3. 信效度 (EFA/CFA)',
      subtitle: 'Cronbach α、AVE/CR、EFA 平行分析与 Harman CMB 检验',
      icon: '📏',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('measurement')
        onClose()
      },
    },
    {
      id: 'tab_regression',
      category: 'empirical_tab',
      title: '实证分区: 5. 分层回归',
      subtitle: '分区块R²、ΔR²、稳健标准误与影响点敏感性',
      icon: '📐',
      action: () => {
        onSelectView('empirical')
        if (onSelectEmpiricalTab) onSelectEmpiricalTab('regression')
        onClose()
      },
    },
  ]

  if (onLoadDemo) {
    list.push({
      id: 'action_demo',
      category: 'action',
      title: '快捷操作: 一键加载当前时间结构示例项目',
      subtitle: '按当前选择导入横截面、追踪面板或密集追踪示例数据',
      icon: '🚀',
      action: () => {
        onLoadDemo()
        onClose()
      },
    })
  }

  for (const v of variables) {
    list.push({
      id: `var_${v.id}`,
      category: 'variable',
      title: `变量: ${v.label} (${v.id})`,
      subtitle: '查看数据字典与变量取值分布',
      icon: '🏷️',
      action: () => {
        onSelectView('data')
        onClose()
      },
    })
  }

  return list
}
