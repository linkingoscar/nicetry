import type { EmpiricalAnalysisReport } from '../../types'

type RelativeImportance = NonNullable<
  NonNullable<EmpiricalAnalysisReport['hierarchicalRegression']>['relativeImportance']
>

interface RelativeImportanceTableProps {
  result: RelativeImportance
  metric: (value: number | null | undefined, digits?: number) => string
}

export function RelativeImportanceTable({
  result,
  metric,
}: RelativeImportanceTableProps) {
  if (!result.available) {
    return <p className="method-note">相对重要性不可用：{result.reason ?? '原因未记录'}</p>
  }
  return (
    <div className="table-wrap" style={{ marginTop: '1.25rem' }}>
      <strong>预测变量相对重要性（精确 Shapley/LMG）</strong>
      <p className="method-note">
        控制变量模型 R²={metric(result.baseRSquared)}；完整模型 R²={metric(result.fullRSquared)}；
        焦点预测变量 ΔR²={metric(result.incrementalRSquared)}。贡献是对全部
        {result.subsetModelCount} 个子集模型的精确顺序平均，不等同于标准化 β。
      </p>
      <table className="result-table empirical-table">
        <thead><tr><th>排名</th><th>预测变量</th><th>贡献 ΔR²</th><th>占焦点 ΔR²</th></tr></thead>
        <tbody>{result.rows?.map((row) => (
          <tr key={row.id}>
            <td>{row.rank}</td><th>{row.label}</th><td>{metric(row.contribution)}</td>
            <td>{row.percentIncrementalRSquared == null ? '—' : `${metric(row.percentIncrementalRSquared, 1)}%`}</td>
          </tr>
        ))}</tbody>
      </table>
      <p className="method-note">贡献之和={metric(result.contributionSum)}；相关预测变量的共享解释量按所有进入顺序公平分摊，不据此自动宣称因果重要性。</p>
    </div>
  )
}
