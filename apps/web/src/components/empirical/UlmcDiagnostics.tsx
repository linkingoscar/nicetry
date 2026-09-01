import { metric, probability } from './resultFormatters'
import { ScrollableResultTable } from '../shared/ScrollableResultTable'

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}
function number(value: unknown) { return typeof value === 'number' ? value : null }

export function UlmcDiagnostics({ result }: { result?: Record<string, unknown> }) {
  if (!result?.available) return <p className="method-warning">ULMC 未完成：{typeof result?.reason === 'string' ? result.reason : '无可用结果'}。</p>
  const comparison = record(result.modelComparison)
  return <section className="evidence-section">
    <h3>未测量潜方法因子（ULMC）</h3>
    <ScrollableResultTable label="ULMC 模型比较表（可横向滚动）"><table className="result-table">
      <thead><tr><th>模型</th><th>χ²</th><th>df</th><th>CFI</th><th>RMSEA</th></tr></thead>
      <tbody>{[['基准模型', result.baselineModel], ['方法因子模型', result.ulmcModel]].map(([label, model]) => {
        const values = record(model)
        return <tr key={String(label)}><th>{String(label)}</th><td>{metric(number(values.chisq))}</td><td>{metric(number(values.df))}</td><td>{metric(number(values.cfi))}</td><td>{metric(number(values.rmsea))}</td></tr>
      })}</tbody>
    </table></ScrollableResultTable>
    <p>Δχ²={metric(number(comparison.deltaChisq))}，Δdf={metric(number(comparison.deltaDf))}，p={probability(number(comparison.pValue))}；ΔCFI={metric(number(comparison.deltaCfi))}。</p>
    {typeof result.methodologicalWarning === 'string' ? <p className="method-warning">{result.methodologicalWarning}</p> : null}
  </section>
}
