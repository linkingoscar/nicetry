import type { EmpiricalAnalysisReport } from '../../types'

interface PaperReadySummaryTableProps {
  table: NonNullable<EmpiricalAnalysisReport['paperSummaryTable']>
  metric: (value: number | null | undefined) => string
  significance: (value: number | null | undefined) => string
}

export function PaperReadySummaryTable({
  table,
  metric,
  significance,
}: PaperReadySummaryTableProps) {
  const confidenceLabel = `${Number((table.confidenceLevel * 100).toFixed(2))}% CI`
  return (
    <section className="evidence-section" aria-labelledby="paper-summary-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Descriptive summary</p>
          <h2 id="paper-summary-heading">描述统计、信度与相关整合表</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              <th>#</th><th>变量</th><th>N</th><th>M</th><th>SD</th><th>α</th><th>ω</th>
              {table.variables.map((variable, index) => <th key={variable.id}>{index + 1}</th>)}
            </tr>
          </thead>
          <tbody>
            {table.rows.map((row, rowIndex) => (
              <tr key={row.id}>
                <td>{rowIndex + 1}</td><th scope="row">{row.label}</th><td>{row.n}</td>
                <td>{metric(row.mean)}</td><td>{metric(row.sd)}</td>
                <td>{metric(row.alpha)}</td><td>{metric(row.omega)}</td>
                {row.correlations.map((coefficient, columnIndex) => (
                  <td
                    key={`${row.id}-${table.variables[columnIndex]?.id}`}
                    title={columnIndex <= rowIndex
                      ? `N=${row.counts[columnIndex]}；${confidenceLabel} [${metric(row.ciLower[columnIndex])}, ${metric(row.ciUpper[columnIndex])}]`
                      : undefined}
                  >
                    {columnIndex <= rowIndex
                      ? `${metric(coefficient)}${significance(row.pValues[columnIndex])}`
                      : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="method-note">本表为描述-相关汇总，不声明 publicationEligible；当前 publication gate 未批准任何“论文级”标签。α/ω 仅用于构念量表；观测变量显示为“—”。相关采用成对完整观测，悬停可查看每一对的 N 与 {confidenceLabel}。</p>
    </section>
  )
}
