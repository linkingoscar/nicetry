import type { LongitudinalPanelResult } from '../../types'

interface LongitudinalCmbResultProps {
  result: LongitudinalPanelResult
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function LongitudinalCmbResult({
  result,
  metric,
  probability,
}: LongitudinalCmbResultProps) {
  const cmb = result.cmbSensitivity
  if (!cmb) return null
  return (
    <section className="analysis-result-subsection" aria-labelledby="longitudinal-cmb-heading">
      <div className="section-heading">
        <h3 id="longitudinal-cmb-heading">纵向共同方法偏差敏感性</h3>
        <span className={`status-chip ${cmb.validForInterpretation ? '' : 'is-warning'}`}>
          {cmb.validForInterpretation ? '识别检查通过' : '不得解释'}
        </span>
      </div>
      {cmb.diagnostics.length ? (
        <div className="diagnostic-list" role="alert">
          {cmb.diagnostics.map((diagnostic) => (
            <p key={`${diagnostic.code}-${diagnostic.message}`}>{diagnostic.message}</p>
          ))}
        </div>
      ) : null}
      {cmb.available ? (
        <>
          <dl className="run-meta factor-meta">
            <div><dt>方法</dt><dd>{cmb.method}</dd></div>
            <div><dt>方法因子题项</dt><dd>{cmb.indicatorCount}</dd></div>
            <div><dt>标记题项</dt><dd>{cmb.markerItemId}</dd></div>
            <div>
              <dt>平均标准化方法方差</dt>
              <dd>{metric(cmb.averageStandardizedVarianceShare)}</dd>
            </div>
            <div><dt>推断改变路径</dt><dd>{cmb.changedInferenceCount}</dd></div>
            <div>
              <dt>信息矩阵</dt>
              <dd>{cmb.identification?.informationFullRank ? '满秩' : '未通过'}</dd>
            </div>
          </dl>
          <p className="method-note">{cmb.interpretation}</p>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr>
                  <th>路径</th><th>时段</th><th>基准 B</th><th>ULMC B</th>
                  <th>相对变化</th><th>基准 p</th><th>ULMC p</th><th>推断改变</th>
                </tr>
              </thead>
              <tbody>
                {cmb.pathChanges?.filter((path) => path.pathType === 'cross_lagged').map((path) => (
                  <tr key={path.id}>
                    <th>{path.direction}</th>
                    <td>T{path.fromWave}→T{path.toWave}</td>
                    <td>{metric(path.baselineEstimate)}</td>
                    <td>{metric(path.adjustedEstimate)}</td>
                    <td>{metric(path.relativeChange)}</td>
                    <td>{probability(path.baselinePValue)}</td>
                    <td>{probability(path.adjustedPValue)}</td>
                    <td>{path.inferenceChanged ? '是' : '否'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <p className="method-note">方法因子模型未达到预先规定的测量或识别门槛。</p>
      )}
    </section>
  )
}
