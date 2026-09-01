import type { SemResult } from '../../types'

interface SemResultViewProps {
  semResult: SemResult
}

export function SemResultView({ semResult }: SemResultViewProps) {
  const { fitIndices, loadings, paths, reliability } = semResult

  const firstOrderLoadings = loadings.filter((l) => l.level !== 'higher_order')
  const higherOrderLoadings = loadings.filter((l) => l.level === 'higher_order')

  return (
    <div className="sem-result-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Structural Equation Modeling</p>
          <h3>高阶 SEM 估计结果与全路径分析</h3>
        </div>
      </div>

      {/* 整体模型拟合指标 */}
      <div className="fit-indices-grid">
        <div className="fit-card">
          <span className="fit-label">χ² (df)</span>
          <span className="fit-value">
            {fitIndices.chiSquare?.toFixed(3) ?? '—'} ({fitIndices.df ?? '—'})
          </span>
          <small>p = {fitIndices.pValue !== null ? fitIndices.pValue.toFixed(3) : '—'}</small>
        </div>
        <div className="fit-card">
          <span className="fit-label">CFI</span>
          <span className={`fit-value ${fitIndices.cfi && fitIndices.cfi >= 0.95 ? 'is-good' : ''}`}>
            {fitIndices.cfi?.toFixed(3) ?? '—'}
          </span>
          <small>标准 &ge; .95</small>
        </div>
        <div className="fit-card">
          <span className="fit-label">TLI</span>
          <span className={`fit-value ${fitIndices.tli && fitIndices.tli >= 0.95 ? 'is-good' : ''}`}>
            {fitIndices.tli?.toFixed(3) ?? '—'}
          </span>
          <small>标准 &ge; .95</small>
        </div>
        <div className="fit-card">
          <span className="fit-label">RMSEA</span>
          <span className={`fit-value ${fitIndices.rmsea && fitIndices.rmsea <= 0.08 ? 'is-good' : ''}`}>
            {fitIndices.rmsea?.toFixed(3) ?? '—'}
          </span>
          <small>标准 &le; .08</small>
        </div>
        <div className="fit-card">
          <span className="fit-label">SRMR</span>
          <span className={`fit-value ${fitIndices.srmr && fitIndices.srmr <= 0.08 ? 'is-good' : ''}`}>
            {fitIndices.srmr?.toFixed(3) ?? '—'}
          </span>
          <small>标准 &le; .08</small>
        </div>
      </div>

      {/* 高阶潜变量载荷 */}
      {higherOrderLoadings.length > 0 && (
        <div className="sem-section">
          <h4>高阶潜因素测量载荷 (Higher-Order Factor Loadings γ)</h4>
          <div className="table-responsive">
            <table className="table apa-table">
              <thead>
                <tr>
                  <th>高阶构念</th>
                  <th>低阶潜因子</th>
                  <th>未标准化 B</th>
                  <th>标准误 SE</th>
                  <th>z 值</th>
                  <th>P 值</th>
                  <th>标准化 γ (Std.all)</th>
                  <th>SMC (R²)</th>
                </tr>
              </thead>
              <tbody>
                {higherOrderLoadings.map((item) => {
                  const smc = (item.stdAll ** 2).toFixed(3)
                  return (
                    <tr key={`${item.latentId}-${item.indicatorId}`}>
                      <td><strong>{item.latentId}</strong></td>
                      <td>{item.indicatorId}</td>
                      <td>{item.estimate.toFixed(3)}</td>
                      <td>{item.standardError?.toFixed(3) ?? '—'}</td>
                      <td>{item.statistic?.toFixed(3) ?? '—'}</td>
                      <td>{item.pValue !== null ? (item.pValue < .001 ? '< .001' : item.pValue.toFixed(3)) : '—'}</td>
                      <td><strong>{item.stdAll.toFixed(3)}</strong></td>
                      <td><span className="pill-chip">{smc}</span></td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 一阶测量模型与信效度 */}
      <div className="sem-section">
        <h4>一阶测量载荷与构念信效度 (First-Order Measurement & Reliability)</h4>
        <div className="table-responsive">
          <table className="table apa-table">
            <thead>
              <tr>
                <th>潜变量</th>
                <th>观测题项</th>
                <th>未标准化 B</th>
                <th>SE</th>
                <th>z</th>
                <th>p</th>
                <th>Std.all (λ)</th>
              </tr>
            </thead>
            <tbody>
              {firstOrderLoadings.map((item) => (
                <tr key={`${item.latentId}-${item.indicatorId}`}>
                  <td>{item.latentId}</td>
                  <td>{item.indicatorId}</td>
                  <td>{item.estimate.toFixed(3)}</td>
                  <td>{item.standardError?.toFixed(3) ?? '—'}</td>
                  <td>{item.statistic?.toFixed(3) ?? '—'}</td>
                  <td>{item.pValue !== null ? (item.pValue < .001 ? '< .001' : item.pValue.toFixed(3)) : '—'}</td>
                  <td>{item.stdAll.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {reliability.length > 0 && (
          <div className="reliability-grid">
            {reliability.map((rel) => {
              const crSuppressed = rel.compositeReliabilityReason === 'suppressed_correlated_residuals'
              return (
                <div className="rel-card" key={rel.latentId}>
                  <strong>{rel.latentId}</strong>
                  <div className="rel-metrics">
                    <span>Cronbach's α: <strong>{rel.cronbachAlpha?.toFixed(3) ?? '—'}</strong></span>
                    {typeof rel.alphaSampleSize === 'number' ? (
                      <small>α N = {rel.alphaSampleSize}</small>
                    ) : null}
                    <span>
                      McDonald's ω:{' '}
                      <strong>{crSuppressed ? '—' : rel.mcdonaldOmega?.toFixed(3) ?? '—'}</strong>
                    </span>
                    <span>
                      CR:{' '}
                      <strong>
                        {crSuppressed ? '—（存在相关残差）' : rel.compositeReliability?.toFixed(3) ?? '—'}
                      </strong>
                    </span>
                    <span>AVE: <strong>{rel.ave?.toFixed(3) ?? '—'}</strong></span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 结构路径分析 */}
      <div className="sem-section">
        <h4>结构方程路径系数 (Structural Paths β)</h4>
        <div className="table-responsive">
          <table className="table apa-table">
            <thead>
              <tr>
                <th>源变量</th>
                <th>目标变量</th>
                <th>未标准化 B</th>
                <th>SE</th>
                <th>z</th>
                <th>P 值</th>
                <th>标准化 β</th>
              </tr>
            </thead>
            <tbody>
              {paths.map((p) => (
                <tr key={`${p.from}-${p.to}`}>
                  <td>{p.from}</td>
                  <td>{p.to}</td>
                  <td>{p.estimate.toFixed(3)}</td>
                  <td>{p.standardError?.toFixed(3) ?? '—'}</td>
                  <td>{p.statistic?.toFixed(3) ?? '—'}</td>
                  <td>{p.pValue !== null ? (p.pValue < .001 ? '< .001' : p.pValue.toFixed(3)) : '—'}</td>
                  <td><strong>{p.stdAll.toFixed(3)}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
