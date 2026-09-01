import type { ResultBundle } from '../../types'

export interface DiagnosticItem {
  id: string
  category: 'convergence' | 'heywood' | 'heteroskedasticity' | 'multicollinearity' | 'outlier' | 'info'
  severity: 'error' | 'warning' | 'info'
  title: string
  description: string
  remediation: string
}

export function analyzeDiagnostics(result?: ResultBundle, error?: Error | null): DiagnosticItem[] {
  const items: DiagnosticItem[] = []

  if (error) {
    items.push({
      id: 'err-execution',
      category: 'convergence',
      severity: 'error',
      title: '模型估计运行中断 / 计算错误',
      description: error.message,
      remediation: '建议检查变量确认类型是否包含离群空值，或切换稳健估计器（如 OLS + HC3 标准误）。',
    })
  }

  if (!result) return items

  // 1. Analyze Warnings from ResultBundle
  if (result.warnings && result.warnings.length > 0) {
    for (const [idx, w] of result.warnings.entries()) {
      items.push({
        id: `warn-${idx}`,
        category: w.code.includes('heywood') ? 'heywood' : w.code.includes('matrix') ? 'multicollinearity' : 'convergence',
        severity: w.severity,
        title: `统计警告 (${w.code})`,
        description: w.message,
        remediation: w.code.includes('heywood')
          ? '建议约束残差方差 ≥ 0，或者检查该指标的标准化载荷是否超过 1.0。'
          : w.code.includes('matrix')
            ? '建议开启“自变量均值中心化 (Mean Centering)”以降低共线性风险。'
            : '建议检查样本量或重新设定因子测量模型指标。',
      })
    }
  }

  // 2. Check SEM AVE / Reliability Issues
  if (result.semResult) {
    for (const rel of result.semResult.reliability) {
      if (rel.ave < 0.5) {
        items.push({
          id: `sem-ave-${rel.latentId}`,
          category: 'heywood',
          severity: 'warning',
          title: `潜变量 ${rel.latentId} 收敛效度 (AVE) 偏低 (${rel.ave.toFixed(3)} < 0.5)`,
          description: `潜变量 ${rel.latentId} 的平均方差提取值未达经典 0.5 门槛，可能存在指标载荷较低或测量噪声问题。`,
          remediation: '建议检查标准化载荷低于 0.5 的题项，考虑予以剔除或重构因子归属。',
        })
      }
    }
  }

  // 3. Check Equation Heteroskedasticity
  if (result.diagnostics) {
    for (const diag of result.diagnostics) {
      if (diag.heteroskedasticity && diag.heteroskedasticity.pValue < 0.05) {
        items.push({
          id: `hetero-${diag.equationId}`,
          category: 'heteroskedasticity',
          severity: 'warning',
          title: `方程 ${diag.equationId} 存在显著异方差 (p = ${diag.heteroskedasticity.pValue.toFixed(3)})`,
          description: `Breusch-Pagan 异方差检验显著 (p < .05)，经典 OLS 标准误可能会低估 SE。`,
          remediation: '强烈建议在“算法引擎”配置中开启“HC3 稳健标准误”或使用 5000 次 Bootstrap 重抽样。',
        })
      }
      if (diag.maximumCooksDistance > 1.0) {
        items.push({
          id: `cook-${diag.equationId}`,
          category: 'outlier',
          severity: 'warning',
          title: `方程 ${diag.equationId} 存在强影响力孤立样本 (Cook's D = ${diag.maximumCooksDistance.toFixed(3)})`,
          description: `发现 Cook's Distance > 1.0 的数据点，该极值样本对回归斜率产生了较大牵引。`,
          remediation: '建议在“数据与测量”工作区检查该离群点，或执行敏感性检验对比剔除前后估计值。',
        })
      }
    }
  }

  if (items.length === 0) {
    items.push({
      id: 'all-healthy',
      category: 'info',
      severity: 'info',
      title: '✅ 模型健康诊断状态良好',
      description: '未发现 Heywood Case、严重异方差或收敛异常。拟合与估计质量符合稳健性推断条件。',
      remediation: '可安心导出 APA 标准报告与表格。',
    })
  }

  return items
}
