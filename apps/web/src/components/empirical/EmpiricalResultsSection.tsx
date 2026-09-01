import { EmpiricalProcedureResult } from './EmpiricalProcedureResult'
import { EmpiricalResultsToolbar } from './EmpiricalResultsToolbar'
import { EmpiricalResultsNav } from './EmpiricalResultsNav'
import { EmpiricalResultTabsView } from './EmpiricalResultTabsView'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'

export function EmpiricalResultsSection() {
  const {
    report,
    isConfigStale,
    isContextStale,
    onRun,
    datasetId,
    datasetName,
    measurementVersion,
    summaryQuery,
    correlationQuery,
    efaCfaQuery,
    validityQuery,
    regressionQuery,
    activeTab,
    isPending,
    setActiveTab,
    resultStatus,
    showToast,
    resultsRef,
  } = useEmpiricalAnalysisContext()

  if (!report) return null

  return (
    <div className="empirical-results" id="empirical-results" ref={resultsRef}>
      {isConfigStale ? (
        <div
          className="method-warning"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            margin: '0 0 12px',
            padding: '10px 16px',
            borderRadius: '10px',
          }}
        >
          <span>⚠️ 配置参数已更新，当前显示为上一次估算结果。请点击重新运行。</span>
          <button
            type="button"
            className="run-button"
            style={{ width: 'auto', padding: '6px 14px', fontSize: '11px' }}
            onClick={onRun}
          >
            刷新运行
          </button>
        </div>
      ) : null}
      {isContextStale ? (
        <div className="method-warning" role="alert">
          当前结果绑定的分析上下文已变化；请刷新方法目录并重新运行，避免把旧结构结果用于当前研究。
        </div>
      ) : null}
      {report.warnings?.length ? (
        <details className="method-warning-summary">
          <summary>本次分析有 {report.warnings.length} 条方法提示</summary>
          <ul>
            {report.warnings.map((warning: { code: string; message: string }) => (
              <li key={warning.code}>{warning.message}</li>
            ))}
          </ul>
        </details>
      ) : null}

      <EmpiricalResultsToolbar
        procedure={report.options.procedure}
        datasetId={datasetId}
        datasetName={datasetName}
        measurementVersion={measurementVersion}
        reportId={report.reportId}
        summary={summaryQuery.data ?? undefined}
        correlation={correlationQuery.data ?? undefined}
      />

      {report.options.procedure ? <EmpiricalProcedureResult /> : <>
      <EmpiricalResultsNav
        activeTab={activeTab}
        pending={isPending}
        statusMap={{
          overview: (summaryQuery.data?.commonMethodBias?.firstFactorVariancePercent && summaryQuery.data.commonMethodBias.firstFactorVariancePercent > 40) ? 'warning' : 'available',
          correlation: 'available',
          measurement: (summaryQuery.data?.commonMethodBias?.firstFactorVariancePercent && summaryQuery.data.commonMethodBias.firstFactorVariancePercent > 40) ? 'warning' : 'available',
          groups: resultStatus('groups'),
          regression: resultStatus('regression'),
          advanced: resultStatus('advanced'),
          longitudinal: resultStatus('longitudinal'),
          diary: resultStatus('diary'),
        }}
        onChange={setActiveTab}
      />

      <EmpiricalResultTabsView
        activeTab={activeTab}
        reportId={report.reportId}
        datasetId={datasetId}
        measurementVersion={measurementVersion}
        reportOptions={report.options}
        queries={{ summary: summaryQuery, correlation: correlationQuery, efaCfa: efaCfaQuery, validity: validityQuery, regression: regressionQuery }}
        showToast={showToast}
      />
      </>}
    </div>
  )
}
