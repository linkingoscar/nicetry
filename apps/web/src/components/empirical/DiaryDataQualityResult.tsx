import type { DiaryMultilevelResult } from '../../types'

interface DiaryDataQualityResultProps {
  result: DiaryMultilevelResult
  metric: (value: number | null | undefined, digits?: number) => string
}

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`
}

export function DiaryDataQualityResult({
  result,
  metric,
}: DiaryDataQualityResultProps) {
  const quality = result.dataQuality
  const reliability = result.multilevelReliability ?? []
  if (!quality && reliability.length === 0) return null
  return (
    <div className="longitudinal-evidence-stack">
      {quality ? (
        <>
          <h3>ESM 依从性与响应质量</h3>
          <dl className="run-meta factor-meta">
            <div><dt>提示记录</dt><dd>{quality.observedPromptRows}</dd></div>
            <div>
              <dt>预期/人</dt>
              <dd>{quality.expectedObservationsPerPerson ?? '未指定'}</dd>
            </div>
            <div><dt>总体依从率</dt><dd>{percent(quality.overallComplianceRate)}</dd></div>
            <div>
              <dt>个人依从率中位数</dt>
              <dd>{percent(quality.personCompliance.median)}</dd>
            </div>
            <div>
              <dt>低于阈值</dt>
              <dd>{quality.personCompliance.belowThresholdCount} 人</dd>
            </div>
            {quality.responseLatency ? (
              <>
                <div><dt>响应延迟中位数</dt><dd>{metric(quality.responseLatency.median, 1)}</dd></div>
                <div><dt>响应延迟 P95</dt><dd>{metric(quality.responseLatency.p95, 1)}</dd></div>
                <div><dt>窗口外记录</dt><dd>{quality.responseLatency.outsideWindowCount}</dd></div>
              </>
            ) : null}
          </dl>
        </>
      ) : null}

      {reliability.length ? (
        <>
          <h3>被试内/被试间信度</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>构念</th><th>题项数</th><th>Within α</th><th>Between α</th><th>题项平均 ICC</th></tr>
              </thead>
              <tbody>
                {reliability.map((row) => (
                  <tr key={row.label}>
                    <th>{row.label}</th>
                    <td>{row.itemIds.length}</td>
                    <td>{metric(row.withinAlpha)}</td>
                    <td>{metric(row.betweenAlpha)}</td>
                    <td>{metric(row.meanItemIcc)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="method-note">
            信度分别基于个体内中心化协方差和个体均值协方差计算，不能用单层 α 替代。
          </p>
        </>
      ) : null}
    </div>
  )
}
