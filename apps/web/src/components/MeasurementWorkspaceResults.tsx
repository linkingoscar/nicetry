import type { MeasurementVersion } from '../types'
import { formatMetric } from './measurementWorkspaceUtils'
import { ReliabilityReport } from './MeasurementReliabilityReport'

export function MeasurementWorkspaceResults({
  measurement,
}: {
  measurement: MeasurementVersion
}) {
  return (
    <div className="measurement-results">
      <div className="ready-banner">
        <div><strong>测量层已完成 · v{measurement.version}</strong><span>派生数据已准备进入实证分析与模型画布</span></div>
        <code>{measurement.derivedDataset.id}</code>
      </div>
      {measurement.warnings.map((warning) => (
        <p className="method-warning" key={warning.message}>{warning.message}</p>
      ))}
      {measurement.reports.map((report) => (
        <ReliabilityReport
          key={report.constructId}
          report={report}
          constructName={measurement.constructs.find((construct) => construct.id === report.constructId)?.name ?? report.constructId}
        />
      ))}
      <section className="score-preview" aria-labelledby="score-preview-heading">
        <strong id="score-preview-heading">转换预览（前 {measurement.transformationPreview.length} 行）</strong>
        <div className="table-wrap">
          <table className="variable-table">
            <thead>
              <tr>
                <th scope="col">行</th>
                {measurement.derivedDataset.scoreVariables.map((variable) => (
                  <th scope="col" key={variable.id}>{variable.label}<small>{variable.id}</small></th>
                ))}
              </tr>
            </thead>
            <tbody>
              {measurement.transformationPreview.map((row, index) => (
                <tr key={measurement.derivedDataset.scoreVariables.map((variable) => `${variable.id}:${row[variable.id] ?? 'missing'}`).join('|')}>
                  <th scope="row">{index + 1}</th>
                  {measurement.derivedDataset.scoreVariables.map((variable) => (
                    <td key={variable.id}>{row[variable.id] === null ? '缺失' : formatMetric(row[variable.id], 3)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="transformation-log">
        <strong>转换日志</strong>
        {measurement.changeNote ? <p>版本说明：{measurement.changeNote}</p> : null}
        {measurement.transformationLog.map((entry) => <p key={entry.constructId}>{entry.message}</p>)}
      </div>
    </div>
  )
}
