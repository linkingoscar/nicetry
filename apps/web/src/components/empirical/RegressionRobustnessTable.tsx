import type { EmpiricalAnalysisReport } from '../../types'

type Regression = NonNullable<EmpiricalAnalysisReport['hierarchicalRegression']>

interface RegressionRobustnessTableProps {
  robustness: NonNullable<Regression['robustness']>
  metric: (value: number | null | undefined) => string
  probability: (value: number | null | undefined) => string
}

export function RegressionRobustnessTable({
  robustness,
  metric,
  probability,
}: RegressionRobustnessTableProps) {
  const influence = robustness.influence
  return (
    <article className="regression-block">
      <div>
        <strong>稳健性与敏感性比较</strong>
        <span>标记 {influence.influentialCount} 个高影响观测；主模型未自动删除</span>
      </div>
      <p className="method-note">
        Cook 距离阈值={metric(influence.cookDistanceCutoff)}，杠杆值阈值={metric(influence.leverageCutoff)}；
        敏感性样本保留 N={influence.retainedCount}。
      </p>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>变量</th><th>B</th><th>经典 SE</th><th>经典 p</th><th>HC3 SE</th><th>HC3 p</th></tr></thead>
          <tbody>{robustness.standardErrorComparison.map((row) => (
            <tr key={row.term}>
              <th scope="row">{row.label}</th><td>{metric(row.estimate)}</td>
              <td>{metric(row.classicStandardError)}</td><td>{probability(row.classicPValue)}</td>
              <td>{metric(row.hc3StandardError)}</td><td>{probability(row.hc3PValue)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>变量</th><th>未加控制 B</th><th>完整模型 B</th><th>剔除高影响观测 B</th><th>控制后变号</th><th>敏感性变号</th></tr></thead>
          <tbody>{robustness.coefficientStability.map((row) => (
            <tr key={row.term}>
              <th scope="row">{row.label}</th><td>{metric(row.unadjustedEstimate)}</td>
              <td>{metric(row.adjustedEstimate)}</td><td>{metric(row.withoutInfluentialEstimate)}</td>
              <td>{row.signChangedAfterControls == null ? '—' : row.signChangedAfterControls ? '是' : '否'}</td>
              <td>{row.signChangedWithoutInfluential == null ? '—' : row.signChangedWithoutInfluential ? '是' : '否'}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="method-note">该结果用于敏感性核查，不把数据驱动的个案排除替代预设排除规则，也不自动改变主模型结论。</p>
    </article>
  )
}
