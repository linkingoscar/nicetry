import type { MeasurementReport } from '../types'
import { formatMetric, formatPercent } from './measurementWorkspaceUtils'
import styles from './MeasurementWorkspace.module.css'

export function ReliabilityReport({
  report,
  constructName,
}: {
  report: MeasurementReport
  constructName: string
}) {
  return (
    <section className="measurement-report" aria-labelledby={`report-${report.constructId}`}>
      <div className="section-heading dictionary-heading-row">
        <div>
          <p className="eyebrow">测量检查</p>
          <h2 id={`report-${report.constructId}`}>{constructName}</h2>
        </div>
        <span className="status-chip">{report.outputVariableId}</span>
      </div>
      <div className="reliability-grid">
        <div>
          <span>Cronbach's α</span>
          <strong>
            {formatMetric(report.alpha)}
            {report.alpha !== null && report.alpha >= 0.70 ? (
              <span className={`benchmark-badge is-good ${styles.benchmarkBadge}`}>Good (良好)</span>
            ) : report.alpha !== null && report.alpha >= 0.60 ? (
              <span className={`benchmark-badge ${styles.benchmarkBadge} ${styles.benchmarkBadgeAcceptable}`}>Acceptable</span>
            ) : report.alpha !== null ? (
              <span className={`benchmark-badge is-warning ${styles.benchmarkBadge}`}>Alert / 偏低</span>
            ) : null}
          </strong>
        </div>
        <div>
          <span>McDonald's ω</span>
          <strong>
            {formatMetric(report.omega)}
            {report.omega !== null && report.omega >= 0.70 ? (
              <span className={`benchmark-badge is-good ${styles.benchmarkBadge}`}>Good (良好)</span>
            ) : report.omega !== null && report.omega >= 0.60 ? (
              <span className={`benchmark-badge ${styles.benchmarkBadge} ${styles.benchmarkBadgeAcceptable}`}>Acceptable</span>
            ) : report.omega !== null ? (
              <span className={`benchmark-badge is-warning ${styles.benchmarkBadge}`}>Alert / 偏低</span>
            ) : null}
          </strong>
        </div>
        <div><span>完整案例</span><strong>{report.completeCaseCount}</strong></div>
        <div><span>有效得分</span><strong>{report.scoreDistribution.validCount}</strong></div>
        <div><span>得分均值</span><strong>{formatMetric(report.scoreDistribution.mean, 2)}</strong></div>
        <div><span>得分标准差</span><strong>{formatMetric(report.scoreDistribution.standardDeviation, 2)}</strong></div>
      </div>
      <p className="method-note">信度系数不使用固定阈值自动判定“可靠”；删题须同时考虑理论、题项内容与统计证据。</p>
      <div className="table-wrap">
        <table className="variable-table item-analysis-table">
          <thead>
            <tr>
              <th scope="col">题项</th>
              <th scope="col">均值 / SD</th>
              <th scope="col">缺失</th>
              <th scope="col">地板 / 天花板</th>
              <th scope="col">校正项目–总分 r</th>
              <th scope="col">删题后 α / ω</th>
            </tr>
          </thead>
          <tbody>
            {report.itemAnalysis.map((item) => (
              <tr key={item.itemId}>
                <th scope="row">
                  <strong>{item.label}</strong>
                  {item.reversed ? <small className="reverse-badge">反向计分</small> : null}
                </th>
                <td>{formatMetric(item.mean, 2)} / {formatMetric(item.standardDeviation, 2)}</td>
                <td>{item.missingCount}</td>
                <td>{formatPercent(item.floorRate)} / {formatPercent(item.ceilingRate)}</td>
                <td>{formatMetric(item.correctedItemTotalCorrelation)}</td>
                <td>{formatMetric(item.alphaIfDeleted)} / {formatMetric(item.omegaIfDeleted)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
