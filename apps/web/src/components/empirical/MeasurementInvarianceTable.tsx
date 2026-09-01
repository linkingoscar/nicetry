import type { EmpiricalAnalysisReport } from '../../types'

type Invariance = NonNullable<EmpiricalAnalysisReport['measurementInvariance']>

interface MeasurementInvarianceTableProps {
  result: Invariance
  metric: (value: number | null | undefined) => string
  probability: (value: number | null | undefined) => string
}

const levelLabels: Record<string, string> = {
  configural: '配置等值',
  metric: '载荷等值',
  scalar: '截距等值',
  strict: '残差等值',
}

export function MeasurementInvarianceTable({
  result,
  metric,
  probability,
}: MeasurementInvarianceTableProps) {
  if (!result.available) {
    return <p className="method-warning">测量等值性不可用：{result.reason ?? '模型未能估计。'}</p>
  }
  const models = Object.entries(result.models ?? {})
  const comparisons = Object.entries(result.comparisons ?? {})
  return (
    <section className="evidence-section" aria-labelledby="invariance-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Measurement invariance</p><h2 id="invariance-heading">多组测量等值性</h2></div>
      </div>
      <p className="method-note">
        分组：{result.groupLevels?.map((level, index) => `${level} (N=${result.groupSizes?.[index] ?? '—'})`).join('；')}；
        估计样本 N={result.sampleSize}。
      </p>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>层级</th><th>χ²</th><th>df</th><th>CFI</th><th>Robust CFI</th><th>RMSEA</th><th>Robust RMSEA</th><th>SRMR</th></tr></thead>
          <tbody>{models.map(([level, model]) => (
            <tr key={level}>
              <th scope="row">{levelLabels[level] ?? level}</th>
              <td>{metric(model?.chiSquareScaled ?? model?.chiSquare)}</td><td>{metric(model?.df)}</td>
              <td>{metric(model?.cfi)}</td><td>{metric(model?.cfiRobust)}</td>
              <td>{metric(model?.rmsea)}</td><td>{metric(model?.rmseaRobust)}</td><td>{metric(model?.srmr)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>相邻比较</th><th>Δχ²</th><th>Δdf</th><th>p</th><th>ΔCFI</th><th>ΔRMSEA</th><th>口径</th></tr></thead>
          <tbody>{comparisons.map(([level, comparison]) => (
            <tr key={level}>
              <th scope="row">{levelLabels[level] ?? level}</th>
              <td>{metric(comparison.deltaChiSquare)}</td><td>{metric(comparison.deltaDf)}</td>
              <td>{probability(comparison.pValue)}</td><td>{metric(comparison.deltaCfi)}</td>
              <td>{metric(comparison.deltaRmsea)}</td><td>{comparison.fitIndexBasis}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="method-note">系统呈现配置、载荷、截距及残差约束的逐级证据，不用单一 ΔCFI、ΔRMSEA 或 χ² 阈值自动宣布跨组可比。</p>
    </section>
  )
}
