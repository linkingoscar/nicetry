import type { EmpiricalAnalysisSegmentMap } from '../../types'
import type { SegmentQueryState } from './segmentQuery'

import { metric, probability } from './resultFormatters'
import { MeasurementInvarianceTable } from './MeasurementInvarianceTable'
import { DiagnosticAlertCard } from '../shared/DiagnosticAlertCard'
import { SegmentLoader } from './EmpiricalBadges'

interface EmpiricalValidityTabProps {
  query: SegmentQueryState<EmpiricalAnalysisSegmentMap['validity']>
}

export function EmpiricalValidityTab({ query }: EmpiricalValidityTabProps) {
if (query.isLoading) return <SegmentLoader />
if (query.isError) return <div className="error-banner">加载效度数据失败: {String(query.error)}</div>
const data = query.data
if (!data?.validity) return null
const validityExecution = data.validity.methodExecution
const htmtExecution = data.validity.htmtMethodExecution
return (
  <>
    <section className="evidence-section" aria-labelledby="validity-heading">
    <div className="section-heading"><div><p className="eyebrow">CFA & validity</p><h2 id="validity-heading">验证性因子与聚合/区分效度</h2></div></div>
    {validityExecution?.fallbackApplied ? (
      <DiagnosticAlertCard
        type="warning"
        title="效度指标使用近似载荷"
        subtitle={`${validityExecution.requestedMethod} → ${validityExecution.executedMethod}`}
        recommendation="这些 CR、AVE 和 Fornell–Larcker 对角线仅供探索性诊断，不应表述为 CFA 标准化解。"
      >
        <p>回退原因：{validityExecution.fallbackReason ?? 'CFA 标准化载荷不可用。'}</p>
        <p>{validityExecution.interpretationBoundary}</p>
      </DiagnosticAlertCard>
    ) : null}
    {htmtExecution ? (
      <DiagnosticAlertCard
        type={data.validity.htmtAvailable === false ? 'warning' : 'note'}
        title={data.validity.htmtAvailable === false ? 'HTMT 未运行' : 'HTMT 相关矩阵来源'}
        subtitle={`${htmtExecution.requestedMethod} → ${htmtExecution.executedMethod}`}
        recommendation={htmtExecution.interpretationBoundary ?? undefined}
      >
        <p>相关基础：{data.validity.htmtCorrelationSource === 'polychoric' ? 'polychoric（有序题项）' : data.validity.htmtCorrelationSource === 'pearson' ? 'Pearson（连续题项）' : '混合尺度，当前不执行'}</p>
        {data.validity.htmtReason ? <p>原因：{data.validity.htmtReason}</p> : null}
      </DiagnosticAlertCard>
    ) : null}
    <div className="table-wrap">
      <table className="result-table empirical-table">
        <thead><tr><th>构念</th><th>α</th><th>ω</th><th>CR</th><th>AVE</th><th>√AVE</th><th>载荷来源</th><th>Fornell–Larcker</th></tr></thead>
        <tbody>{data.validity.constructs.map((row) => (
          <tr key={row.constructId}>
            <th>{row.label}</th>
            <td>{metric(row.alpha)} {row.alpha !== null && row.alpha >= 0.7 ? <span className="benchmark-badge is-good" style={{ fontSize: '9px', padding: '1px 5px' }}>≥.7</span> : null}</td>
            <td>{metric(row.omega)} {row.omega !== null && row.omega >= 0.7 ? <span className="benchmark-badge is-good" style={{ fontSize: '9px', padding: '1px 5px' }}>≥.7</span> : null}</td>
            <td>{metric(row.compositeReliability)} {row.compositeReliability !== null && row.compositeReliability >= 0.7 ? <span className="benchmark-badge is-good" style={{ fontSize: '9px', padding: '1px 5px' }}>CR≥.7</span> : null}</td>
            <td>{metric(row.averageVarianceExtracted)} {row.averageVarianceExtracted !== null && row.averageVarianceExtracted >= 0.5 ? <span className="benchmark-badge is-good" style={{ fontSize: '9px', padding: '1px 5px' }}>AVE≥.5</span> : null}</td>
            <td>{metric(row.sqrtAve)}</td>
            <td>{row.loadingSource === 'CFA' ? 'CFA 标准化载荷' : '单因子特征分解近似'}</td>
            <td>
              <span className={`benchmark-badge ${row.discriminantValidityPass ? 'is-pass' : 'is-review'}`}>
                {row.discriminantValidityPass ? '通过描述性检查' : '需复核'}
              </span>
            </td>
          </tr>
        ))}</tbody>
      </table>
    </div>
    <div className="validity-matrices">
      <div className="table-wrap"><strong>Fornell–Larcker 矩阵</strong><table className="result-table matrix-table"><thead><tr><th></th>{data.validity.constructLabels.map((label) => <th key={label}>{label}</th>)}</tr></thead><tbody>{data.validity.constructLabels.map((label, rowIndex) => <tr key={label}><th>{label}</th>{data.validity.fornellLarcker[rowIndex].map((value, index) => <td key={data.validity.constructLabels[index]}>{metric(value)}</td>)}</tr>)}</tbody></table></div>
      {data.validity.htmtAvailable === false ? null : <div className="table-wrap">
        <strong>HTMT 矩阵及 95% Bootstrap 置信区间</strong>
        <table className="result-table matrix-table">
          <thead>
            <tr>
              <th></th>
              {data.validity.constructLabels.map((label) => <th key={label}>{label}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.validity.constructLabels.map((label, rowIndex) => (
              <tr key={label}>
                <th>{label}</th>
                {data.validity.htmt[rowIndex].map((value, index) => {
                  const lower = data.validity.htmtCiLower?.[rowIndex]?.[index]
                  const upper = data.validity.htmtCiUpper?.[rowIndex]?.[index]
                  const hasCi = lower !== undefined && lower !== null && upper !== undefined && upper !== null && rowIndex > index
                  return (
                    <td key={data.validity.constructLabels[index]}>
                      {metric(value)}
                      {hasCi ? <div style={{ fontSize: '11px', color: '#595d6b', marginTop: '2px' }}>[{metric(lower)}, {metric(upper)}]</div> : null}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>}
    </div>
    </section>
    {data.measurementInvariance?.available !== undefined ? (
      <MeasurementInvarianceTable result={data.measurementInvariance} metric={metric} probability={probability} />
    ) : null}
  </>
)
}
