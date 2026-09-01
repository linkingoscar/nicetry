import type { EmpiricalAnalysisReport } from '../../types'

type ResponseSurface = NonNullable<EmpiricalAnalysisReport['responseSurface']>

interface ResponseSurfaceAnalysisProps {
  result: ResponseSurface
  metric: (value: number | null | undefined) => string
  probability: (value: number | null | undefined) => string
}

export function ResponseSurfaceAnalysis({
  result,
  metric,
  probability,
}: ResponseSurfaceAnalysisProps) {
  if (!result.available) {
    return <p className="method-warning">响应面不可用：{result.reason ?? '模型未能估计。'}</p>
  }
  const grid = result.grid ?? []
  const xValues = [...new Set(grid.map((point) => point.x))].sort((a, b) => a - b)
  const zValues = [...new Set(grid.map((point) => point.z))].sort((a, b) => a - b)
  const predicted = grid.map((point) => point.predicted)
  const range = (values: number[]) => [Math.min(...values), Math.max(...values)] as const
  const [xMin, xMax] = range(xValues)
  const [zMin, zMax] = range(zValues)
  const [yMin, yMax] = range(predicted)
  const normalize = (value: number, minimum: number, maximum: number) =>
    maximum === minimum ? 0.5 : (value - minimum) / (maximum - minimum)
  const project = (point: { x: number; z: number; predicted: number }) => {
    const x = normalize(point.x, xMin, xMax)
    const z = normalize(point.z, zMin, zMax)
    const y = normalize(point.predicted, yMin, yMax)
    return `${300 + (x - z) * 180},${235 + (x + z) * 60 - y * 155}`
  }
  const line = (points: typeof grid) => points.map(project).join(' ')
  return (
    <section className="evidence-section" aria-labelledby="response-surface-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Polynomial regression</p><h2 id="response-surface-heading">响应面：{result.xLabel} × {result.zLabel} → {result.outcomeLabel}</h2></div>
      </div>
      <p className="method-note">N={result.n}，R²={metric(result.rSquared)}，调整 R²={metric(result.adjustedRSquared)}；{result.method}</p>
      {grid.length ? (
        <svg viewBox="0 0 600 360" role="img" aria-label={`${result.xLabel} 与 ${result.zLabel} 的三维预测响应面`} style={{ width: '100%', maxWidth: '720px' }}>
          <title>{result.xLabel} 与 {result.zLabel} 的三维预测响应面</title>
          {zValues.map((z) => <polyline key={`z-${z}`} points={line(grid.filter((point) => point.z === z).sort((a, b) => a.x - b.x))} fill="none" stroke="#2f3d6b" strokeWidth="1.5" />)}
          {xValues.map((x) => <polyline key={`x-${x}`} points={line(grid.filter((point) => point.x === x).sort((a, b) => a.z - b.z))} fill="none" stroke="#868eaa" strokeWidth="1" />)}
          <text x="500" y="330" fontSize="13">{result.xLabel}</text>
          <text x="55" y="330" fontSize="13">{result.zLabel}</text>
          <text x="285" y="25" fontSize="13">{result.outcomeLabel}</text>
        </svg>
      ) : null}
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>响应面组合量</th><th>估计</th><th>SE</th><th>t</th><th>p</th><th>95% CI</th></tr></thead>
          <tbody>{result.surfaceTests?.map((row) => (
            <tr key={row.id}>
              <th scope="row">{row.label}</th><td>{metric(row.estimate)}</td><td>{metric(row.standardError)}</td>
              <td>{metric(row.statistic)}</td><td>{probability(row.pValue)}</td>
              <td>[{metric(row.lower)}, {metric(row.upper)}]</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
      <p className="method-note">驻点（原量尺）：X={metric(result.stationaryPoint?.xRaw)}，Z={metric(result.stationaryPoint?.zRaw)}。响应面只描述观测关联，不自动解释为匹配或不匹配的因果效应。</p>
    </section>
  )
}
