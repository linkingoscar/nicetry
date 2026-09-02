export const METHOD_CATEGORY_ORDER = [
  'descriptives-relations',
  'measurement',
  'group-comparison',
  'regression',
  'mediation-sem',
  'multilevel',
  'longitudinal',
  'diary',
  'experimental-design',
  'missing-data',
  'power',
] as const

export function methodCategoryLabel(categoryId: string): string {
  const labels: Record<string, string> = {
    'descriptives-relations': '描述、数据检查与关系',
    measurement: '量表与测量',
    'group-comparison': '关系与组间差异',
    regression: '回归模型',
    'mediation-sem': '中介、调节与 SEM',
    multilevel: '聚类与多层',
    longitudinal: '纵向面板',
    diary: '日记 / ESM',
    'experimental-design': '实验设计',
    'missing-data': '缺失与多重插补',
    power: '功效与样本量',
  }
  return labels[categoryId] ?? categoryId.replaceAll('-', ' ')
}
