import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import { EmpiricalOverviewTab } from './EmpiricalOverviewTab'
import { EmpiricalMeasurementTab } from './EmpiricalMeasurementTab'
import { EmpiricalValidityTab } from './EmpiricalValidityTab'
import { MeasurementInvarianceTable } from './MeasurementInvarianceTable'
import { EmpiricalResultTabsView } from './EmpiricalResultTabsView'
import { procedureDefinition } from './empiricalProcedures'
import { metric, probability } from './resultFormatters'
import { SegmentLoader } from './EmpiricalBadges'
import { UlmcDiagnostics } from './UlmcDiagnostics'
import { ScrollableResultTable } from '../shared/ScrollableResultTable'
import type { EmpiricalAnalysisOptions } from '../../types'
import type { EmpiricalResultQueries } from './segmentQuery'

interface EmpiricalProcedureResultViewProps {
  reportId: string
  reportOptions: EmpiricalAnalysisOptions
  datasetId: string
  measurementVersion: number | null
  queries: EmpiricalResultQueries
  showToast: (message: string) => void
}

export function EmpiricalProcedureResultView({
  reportId,
  reportOptions,
  datasetId,
  measurementVersion,
  queries,
  showToast,
}: EmpiricalProcedureResultViewProps) {
  const p = reportOptions.procedure
  if (!p) return null
  const {
    summary: summaryQuery,
    correlation: correlationQuery,
    efaCfa: efaCfaQuery,
    validity: validityQuery,
    regression: regressionQuery,
  } = queries
  const definition = procedureDefinition(p)
  let result: import('react').ReactNode
  if (['descriptives', 'frequencies', 'missing'].includes(p)) {
    result = <EmpiricalOverviewTab query={summaryQuery} showToast={showToast} procedure={p} />
  } else if (p === 'efa' || p === 'cfa') {
    result = <EmpiricalMeasurementTab query={efaCfaQuery} summaryQuery={summaryQuery} procedure={p} />
  } else if (p === 'validity') {
    result = <><EmpiricalMeasurementTab query={efaCfaQuery} summaryQuery={summaryQuery} procedure="cfa" /><EmpiricalValidityTab query={validityQuery} /></>
  } else if (p === 'invariance') {
    result = validityQuery.isLoading ? <SegmentLoader /> : validityQuery.isError ? <p role="alert">测量等值性结果加载失败。</p> : validityQuery.data?.measurementInvariance ?
      <MeasurementInvarianceTable result={validityQuery.data.measurementInvariance} metric={metric} probability={probability} /> : null
  } else if (p === 'reliability') {
    result = summaryQuery.isLoading ? <SegmentLoader /> : summaryQuery.isError ? <p role="alert">信度结果加载失败。</p> : <>
      <p className="method-note">α 为标准化 α；ω 来自单因子 minres。每个量表使用其题项完整案例，未重新拟合多构念 CFA。</p>
      {summaryQuery.data?.reliability?.constructs.map((c) => <section className="evidence-section" key={c.constructId}>
        <h3>{c.label} · N={c.n} · {c.itemCount} 题</h3>
        <dl className="run-meta"><div><dt>标准化 α</dt><dd>{metric(c.statistics.alpha)}</dd></div><div><dt>ω</dt><dd>{metric(c.statistics.omega)}</dd></div><div><dt>有序 α</dt><dd>{metric(c.statistics.ordinalAlpha)}</dd></div><div><dt>有序 ω</dt><dd>{metric(c.statistics.ordinalOmega)}</dd></div></dl>
        {c.statistics.reliabilityWarning ? <p className="method-warning">{c.statistics.reliabilityWarning}</p> : null}
        {c.statistics.ordinalReliabilityReason ? <p className="method-note">有序信度未计算：{c.statistics.ordinalReliabilityReason}</p> : null}
        <ScrollableResultTable label={`${c.label}项目诊断表（可横向滚动）`}><table className="result-table"><thead><tr><th>题项</th><th>校正题总相关</th><th>删除后标准化 α</th><th>删除后 ω</th></tr></thead><tbody>
          {c.items.map((item) => <tr key={item.itemId}><th>{item.itemId}</th><td>{metric(item.correctedItemTotalCorrelation)}</td><td>{metric(item.alphaIfDeleted)}</td><td>{metric(item.omegaIfDeleted)}</td></tr>)}
        </tbody></table></ScrollableResultTable>
      </section>)}
    </>
  } else if (p === 'common_method') {
    const cmb = summaryQuery.data?.commonMethodBias
    result = summaryQuery.isLoading ? <SegmentLoader /> : summaryQuery.isError ? <p role="alert">共同方法诊断加载失败。</p> : <>
      <dl className="run-meta"><div><dt>Harman 首因子解释率</dt><dd>{metric(cmb?.firstFactorVariancePercent)}%</dd></div><div><dt>特征值大于 1</dt><dd>{cmb?.eigenvaluesAboveOne ?? '—'}</dd></div></dl>
      <p className="method-note">{cmb?.method}。Harman 或 ULMC 不能单独排除共同方法偏差。</p>
      <UlmcDiagnostics result={cmb?.ulmc} />
    </>
  } else {
    result = <EmpiricalResultTabsView activeTab={definition.tab} reportId={reportId} datasetId={datasetId}
      measurementVersion={measurementVersion} reportOptions={reportOptions}
      queries={{ summary: summaryQuery, correlation: correlationQuery, efaCfa: efaCfaQuery, validity: validityQuery, regression: regressionQuery }} showToast={showToast} />
  }
  return <section aria-label={`${definition.label}结果`}>
    <h2 className="procedure-result-heading" id={`empirical-tab-${definition.tab}`}>{definition.label} · 本次结果</h2>
    {result}
  </section>
}

export function EmpiricalProcedureResult() {
  const {
    report,
    summaryQuery,
    correlationQuery,
    efaCfaQuery,
    validityQuery,
    regressionQuery,
    datasetId,
    measurementVersion,
    showToast,
  } = useEmpiricalAnalysisContext()
  if (!report) return null
  return (
    <EmpiricalProcedureResultView
      reportId={report.reportId}
      reportOptions={report.options}
      datasetId={datasetId}
      measurementVersion={measurementVersion}
      queries={{
        summary: summaryQuery,
        correlation: correlationQuery,
        efaCfa: efaCfaQuery,
        validity: validityQuery,
        regression: regressionQuery,
      }}
      showToast={showToast}
    />
  )
}
