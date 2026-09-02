import type { WorkspaceView } from '../../hooks/workspaceStateTypes'
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
  onSelectView: (view: WorkspaceView) => void
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
  const openAnalysis = (tab?: EmpiricalResultTab) => {
    onSelectView('analyze')
    if (tab && onSelectEmpiricalTab) onSelectEmpiricalTab(tab)
    onClose()
  }

  const list: CommandItem[] = [
    {
      id: 'view_data',
      category: 'workspace',
      title: '跳转: 数据 (Ctrl+1)',
      subtitle: '查看数据、变量、量表、样本和数据结构',
      icon: '📁',
      action: () => {
        onSelectView('data')
        onClose()
      },
    },
    {
      id: 'view_analyze',
      category: 'workspace',
      title: '跳转: 分析 (Ctrl+2)',
      subtitle: '从统一方法入口选择描述、测量、回归、PROCESS、SEM 或高级方法',
      icon: '📊',
      action: () => openAnalysis(),
    },
    {
      id: 'view_output',
      category: 'workspace',
      title: '跳转: 输出 (Ctrl+3)',
      subtitle: '查看已提交分析的运行记录与历史结果',
      icon: '📑',
      action: () => {
        onSelectView('output')
        onClose()
      },
    },
    {
      id: 'action_higher_order_sem',
      category: 'action',
      title: '分析: 高阶 SEM',
      subtitle: '进入统一方法入口后打开高级 SEM 编辑能力',
      icon: '🧬',
      action: () => openAnalysis(),
    },
    {
      id: 'action_multi_group_sem',
      category: 'action',
      title: '分析: 多群组 SEM / 测量等值性',
      subtitle: '进入统一方法入口选择对应方法',
      icon: '👥',
      action: () => openAnalysis(),
    },
    {
      id: 'action_longitudinal_swimlane',
      category: 'empirical_tab',
      title: '分析: 纵向面板',
      subtitle: 'CLPM、RI-CLPM、LCM-SR 与纵向测量等值性',
      icon: '🌊',
      action: () => openAnalysis('longitudinal'),
    },
    {
      id: 'tab_diary',
      category: 'empirical_tab',
      title: '分析: 日记 / ESM',
      subtitle: 'LMM、GLMM、多层中介与 Bayesian DSEM',
      icon: '🗓️',
      action: () => openAnalysis('diary'),
    },
    {
      id: 'tab_overview',
      category: 'empirical_tab',
      title: '分析: 描述与数据检查',
      subtitle: '描述统计、频数与缺失诊断',
      icon: '📈',
      action: () => openAnalysis('overview'),
    },
    {
      id: 'tab_correlation',
      category: 'empirical_tab',
      title: '分析: 相关与偏相关',
      subtitle: 'Pearson、Spearman 与控制变量偏相关',
      icon: '🔗',
      action: () => openAnalysis('correlation'),
    },
    {
      id: 'tab_measurement',
      category: 'empirical_tab',
      title: '分析: 量表与测量',
      subtitle: '信度、EFA、CFA、效度与测量等值性',
      icon: '📏',
      action: () => openAnalysis('measurement'),
    },
    {
      id: 'tab_regression',
      category: 'empirical_tab',
      title: '分析: 回归模型',
      subtitle: '分层回归、相对重要性与响应面',
      icon: '📐',
      action: () => openAnalysis('regression'),
    },
  ]

  if (onLoadDemo) {
    list.push({
      id: 'action_demo',
      category: 'action',
      title: '快捷操作: 加载当前时间结构示例项目',
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
      subtitle: '返回数据工作区查看变量定义与数据',
      icon: '🏷️',
      action: () => {
        onSelectView('data')
        onClose()
      },
    })
  }

  return list
}
