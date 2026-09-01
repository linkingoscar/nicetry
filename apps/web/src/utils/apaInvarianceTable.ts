import type { InvarianceResult } from '../types'
import type { APATableData } from './apaTableFormat'

/**
 * Generates structured APA 7th Table Data for Multi-Group Invariance Testing.
 */
export function generateMultiGroupInvarianceAPATable(invarianceResult: InvarianceResult | null | undefined): APATableData {
  const headers = ['模型阶梯', 'χ²', 'df', 'CFI', 'TLI', 'RMSEA', 'SRMR', 'Δχ²', 'Δdf', 'ΔCFI', 'ΔRMSEA', '判定结论']
  const stageMap: Record<string, string> = {
    configural: 'M1. 形态等值 (Configural)',
    metric: 'M2. 弱等值 (Metric)',
    scalar: 'M3. 强等值 (Scalar)',
    strict: 'M4. 严格等值 (Strict)',
  }

  const rows: string[][] = (invarianceResult?.models || []).map((m) => {
    const comp = (invarianceResult?.comparisons || []).find((c) => c.comparison.startsWith(m.model))
    return [
      stageMap[m.model] || m.model,
      m.fitIndices?.chiSquare?.toFixed(2) ?? '—',
      String(m.fitIndices?.df ?? '—'),
      m.fitIndices?.cfi?.toFixed(3) ?? '—',
      m.fitIndices?.tli?.toFixed(3) ?? '—',
      m.fitIndices?.rmsea?.toFixed(3) ?? '—',
      m.fitIndices?.srmr?.toFixed(3) ?? '—',
      comp?.deltaChiSquare !== undefined && comp?.deltaChiSquare !== null ? comp.deltaChiSquare.toFixed(2) : '—',
      comp?.deltaDf !== undefined && comp?.deltaDf !== null ? String(comp.deltaDf) : '—',
      comp?.deltaCfi !== undefined && comp?.deltaCfi !== null ? comp.deltaCfi.toFixed(3) : '—',
      comp?.deltaRmsea !== undefined && comp?.deltaRmsea !== null ? comp.deltaRmsea.toFixed(3) : '—',
      comp ? (comp.invarianceHolds ? '等值成立' : '需部分释放') : '基准参照',
    ]
  })

  return {
    title: '表 5 多群组测量等值性阶梯检验拟合与比较 (Measurement Invariance Ladder)',
    headers,
    rows,
  }
}
