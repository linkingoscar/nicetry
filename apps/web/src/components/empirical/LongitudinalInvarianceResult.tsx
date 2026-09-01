import type { LongitudinalPanelResult } from '../../types'

interface LongitudinalInvarianceResultProps {
  result: LongitudinalPanelResult
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function LongitudinalInvarianceResult({
  result,
  metric,
  probability,
}: LongitudinalInvarianceResultProps) {
  const invariance = result.measurementInvariance
  if (!invariance) return null
  return (
    <div className="longitudinal-evidence-stack">
      <div className="section-heading">
        <div>
          <h3>纵向测量等值性</h3>
          <p className="muted">
            请求 {invariance.requestedLevel}；结构模型采用 {invariance.selectedLevel} 等值约束。
          </p>
        </div>
        <span className="status-chip">{invariance.indicatorScale === 'ordinal' ? '有序题项' : '连续近似'}</span>
      </div>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              <th>层级</th><th>CFI</th><th>RMSEA</th><th>SRMR</th>
              <th>χ²</th><th>df</th><th>收敛</th>
            </tr>
          </thead>
          <tbody>
            {invariance.models.map((model) => (
              <tr key={model.level}>
                <th>{model.label}</th>
                <td>{metric(model.fitIndices.cfi)}</td>
                <td>{metric(model.fitIndices.rmsea)}</td>
                <td>{metric(model.fitIndices.srmr)}</td>
                <td>{metric(model.fitIndices.chiSquare, 2)}</td>
                <td>{model.fitIndices.degreesOfFreedom ?? '—'}</td>
                <td>{model.converged ? '是' : '否'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              <th>比较</th><th>ΔCFI</th><th>ΔRMSEA</th><th>ΔSRMR</th>
              <th>Δχ² p</th><th>实用标准</th>
            </tr>
          </thead>
          <tbody>
            {invariance.comparisons.map((comparison) => (
              <tr key={`${comparison.from}-${comparison.to}`}>
                <th>{comparison.from} → {comparison.to}</th>
                <td>{metric(comparison.deltaCfi)}</td>
                <td>{metric(comparison.deltaRmsea)}</td>
                <td>{metric(comparison.deltaSrmr)}</td>
                <td>{probability(comparison.pValue)}</td>
                <td>
                  <span className={`status-chip ${comparison.passesPracticalCriteria ? '' : 'is-warning'}`}>
                    {comparison.passesPracticalCriteria ? '通过' : '未通过'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {invariance.partialPositions.length ? (
        <p className="method-note">
          事前释放的部分等值位置：{invariance.partialPositions.join('、')}。论文中应报告理论依据。
        </p>
      ) : null}

      {result.competingModels?.length ? (
        <>
          <h3>竞争模型比较</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>模型</th><th>CFI</th><th>RMSEA</th><th>SRMR</th><th>AIC</th><th>BIC</th></tr>
              </thead>
              <tbody>
                {result.competingModels.map((model) => (
                  <tr key={model.modelType}>
                    <th>{model.modelLabel}</th>
                    <td>{metric(model.fitIndices.cfi)}</td>
                    <td>{metric(model.fitIndices.rmsea)}</td>
                    <td>{metric(model.fitIndices.srmr)}</td>
                    <td>{metric(model.fitIndices.aic, 1)}</td>
                    <td>{metric(model.fitIndices.bic, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <p className="method-note">{invariance.criteriaSource}</p>
    </div>
  )
}
