import type { LongitudinalPanelResult } from '../../types'

interface LongitudinalGrowthResultProps {
  result: LongitudinalPanelResult
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function LongitudinalGrowthResult({
  result,
  metric,
  probability,
}: LongitudinalGrowthResultProps) {
  const growth = result.growthModel
  if (!growth) return null
  return (
    <section className="analysis-result-subsection" aria-labelledby="lcm-growth-heading">
      <h3 id="lcm-growth-heading">潜在生长轨迹</h3>
      <dl className="run-meta factor-meta">
        <div><dt>轨迹形式</dt><dd>{growth.growthShape}</dd></div>
        <div><dt>时间原点</dt><dd>{metric(growth.timeOrigin)}</dd></div>
        <div><dt>时间载荷</dt><dd>{growth.timeLoadings.join(', ')}</dd></div>
        <div>
          <dt>识别检查</dt>
          <dd>{growth.identification.valid ? '通过' : '需复核'}</dd>
        </div>
        <div>
          <dt>潜变量协方差最小特征值</dt>
          <dd>{metric(growth.identification.latentCovarianceMinimumEigenvalue)}</dd>
        </div>
      </dl>
      <p className="method-note">{growth.interpretation}</p>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr><th>成分</th><th>参数</th><th>估计</th><th>SE</th><th>95% CI</th><th>p</th></tr>
          </thead>
          <tbody>
            {growth.components.map((component, index) => (
              <tr key={`${component.lhs}-${component.operator}-${component.rhs ?? index}`}>
                <th>{component.lhs}</th>
                <td>{component.operator === '~1' ? '均值' : `与 ${component.rhs} 的（协）方差`}</td>
                <td>{metric(component.estimate)}</td>
                <td>{metric(component.standardError)}</td>
                <td>[{metric(component.lower)}, {metric(component.upper)}]</td>
                <td>{probability(component.pValue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
