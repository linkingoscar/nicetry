import type { DiaryMultilevelResult } from '../../types'

interface DiaryGlmmEvidenceResultProps {
  result: DiaryMultilevelResult
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function DiaryGlmmEvidenceResult({
  result,
  metric,
  probability,
}: DiaryGlmmEvidenceResultProps) {
  if (result.analysisType !== 'glmm') return null
  const diagnostics = result.distributionDiagnostics
  return (
    <section className="analysis-result-subsection" aria-labelledby="glmm-evidence-heading">
      <h3 id="glmm-evidence-heading">计数分布与零过程证据</h3>
      {result.methodNotice ? <p className="method-note">{result.methodNotice}</p> : null}
      {diagnostics ? (
        <dl className="run-meta factor-meta">
          <div><dt>计数模型</dt><dd>{result.countModel ?? 'standard'}</dd></div>
          <div><dt>观测零比例</dt><dd>{metric(diagnostics.observedZeroRate)}</dd></div>
          <div><dt>模型预期零比例</dt><dd>{metric(diagnostics.expectedZeroRate)}</dd></div>
          <div><dt>模拟离散比</dt><dd>{metric(diagnostics.dispersionRatio)}</dd></div>
          <div>
            <dt>过度离散模拟 p</dt>
            <dd>{probability(diagnostics.dispersionPValue)}</dd>
          </div>
          <div>
            <dt>过多零值模拟 p</dt>
            <dd>{probability(diagnostics.zeroInflationPValue)}</dd>
          </div>
        </dl>
      ) : null}
      {result.countModelComparison?.length ? (
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead>
              <tr>
                <th>候选模型</th><th>AIC</th><th>BIC</th><th>logLik</th><th>参数数</th><th>收敛</th>
              </tr>
            </thead>
            <tbody>
              {result.countModelComparison.map((row) => (
                <tr key={row.model}>
                  <th>{row.label}</th>
                  <td>{metric(row.aic, 1)}</td>
                  <td>{metric(row.bic, 1)}</td>
                  <td>{metric(row.logLikelihood, 1)}</td>
                  <td>{metric(row.parameterCount, 0)}</td>
                  <td>{row.converged ? '是' : '否'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {result.zeroProcessEffects?.length ? (
        <>
          <h3>零值/门槛过程</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>预测项</th><th>log-odds</th><th>SE</th><th>OR（95% CI）</th><th>p</th></tr>
              </thead>
              <tbody>
                {result.zeroProcessEffects.map((effect) => (
                  <tr key={effect.term}>
                    <th>{effect.label}</th>
                    <td>{metric(effect.estimate)}</td>
                    <td>{metric(effect.standardError)}</td>
                    <td>
                      {metric(effect.exponentiatedEstimate)}
                      {' '}[{metric(effect.exponentiatedLower)}, {metric(effect.exponentiatedUpper)}]
                    </td>
                    <td>{probability(effect.pValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </section>
  )
}
