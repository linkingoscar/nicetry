import type { EmpiricalAnalysisReport } from '../../types'

type MissingReport = NonNullable<EmpiricalAnalysisReport['missingDataReport']>

interface MissingDataReportProps {
  report: MissingReport
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function MissingDataReport({
  report,
  metric,
  probability,
}: MissingDataReportProps) {
  const missingVariables = report.variables.filter((row) => row.missingCount > 0)
  const mcar = report.littleMcar
  const missingPatternLabels = (pattern: MissingReport['patterns'][number]) => (
    Array.isArray(pattern.missingLabels)
      ? pattern.missingLabels
      : Object.values(pattern.missingLabels ?? {})
  )
  return (
    <section className="evidence-section" aria-labelledby="missing-data-heading">
      <div className="section-heading"><div><p className="eyebrow">Missing-data audit</p><h2 id="missing-data-heading">缺失数据报告</h2></div></div>
      <p className="method-note">
        共 {report.rowCount} 行、{report.variableCount} 个报告变量；全变量完整案例
        {report.completeCaseCount}，至少一处缺失 {report.incompleteCaseCount}，缺失单元格
        {report.anyMissingCellCount}。
      </p>
      {missingVariables.length ? (
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead><tr><th>变量</th><th>有效 N</th><th>缺失数</th><th>缺失率</th></tr></thead>
            <tbody>{missingVariables.map((row) => (
              <tr key={row.id}><th>{row.label}</th><td>{row.validCount}</td><td>{row.missingCount}</td><td>{metric((row.missingRate ?? 0) * 100, 1)}%</td></tr>
            ))}</tbody>
          </table>
        </div>
      ) : <p>当前报告变量没有缺失值。</p>}
      {report.patterns.some((pattern) => pattern.missingIds.length > 0) ? (
        <div className="table-wrap" style={{ marginTop: '1rem' }}>
          <strong>主要缺失模式</strong>
          <table className="result-table empirical-table">
            <thead><tr><th>缺失变量</th><th>行数</th><th>比例</th></tr></thead>
            <tbody>{report.patterns.filter((pattern) => pattern.missingIds.length > 0).map((pattern) => (
              <tr key={pattern.missingIds.join('-') || 'missing-pattern'}><td>{missingPatternLabels(pattern).join('、')}</td><td>{pattern.count}</td><td>{metric((pattern.proportion ?? 0) * 100, 1)}%</td></tr>
            ))}</tbody>
          </table>
          {report.patternsTruncated ? <p className="method-note">仅显示频数最高的 20 种模式，其余仍计入模式总数。</p> : null}
        </div>
      ) : null}
      <p className="method-note">
        Little MCAR：{mcar.available
          ? `χ²(${mcar.degreesOfFreedom})=${metric(mcar.statistic)}，p=${probability(mcar.pValue)}；EM ${mcar.emConverged ? '已收敛' : '未在上限内收敛'}（${mcar.emIterations} 次）。`
          : `不可用（${mcar.reason ?? '原因未记录'}）。`}
        {report.guidance}
      </p>
    </section>
  )
}
