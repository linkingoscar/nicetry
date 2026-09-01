import { useCallback, useMemo, useState } from 'react'
import type { AdvancedAnalysisCapability } from '../../types'
import type { ExtendedAdvancedResultResponse } from '../../types/advanced'
import { advancedAnalysisExportUrl } from '../../api/advanced'
import { downloadWithSession } from '../../api/client'
import { EmmConfidencePlot } from './EmmConfidencePlot'
import { FamilyResultTables } from './FamilyResultTables'
import { MethodResultVisuals } from './MethodResultVisuals'
import {
  AdvancedResultHeader,
  EstimatesTable,
  formatNumber,
  formatPower,
  powerSolveLabel,
  type Estimate,
  type SampleFlow,
  type Warning,
} from './AdvancedResultViewSections'

interface AdvancedResultViewProps {
  result: ExtendedAdvancedResultResponse
  capability: AdvancedAnalysisCapability
  jobId: string
  onNewAnalysis: () => void
}

export function AdvancedResultView({ result, capability, jobId, onNewAnalysis }: AdvancedResultViewProps) {
  const bundle = result as Record<string, unknown>
  const warnings = (bundle.warnings ?? []) as Warning[]
  const sampleFlow = (bundle.sampleFlow ?? null) as SampleFlow | null
  const estimates = (bundle.estimates ?? []) as Estimate[]
  const provenance = (bundle.provenance ?? null) as Record<string, unknown> | null
  const familyResult = (bundle.familyResult ?? null) as Record<string, unknown> | null
  const apaReports = (bundle.apaReports ?? []) as string[]
  const estimatedMarginalMeans = familyResult?.family === 'experimental_design'
    && Array.isArray(familyResult.estimatedMarginalMeans)
    ? familyResult.estimatedMarginalMeans.filter(
      (row): row is Record<string, unknown> => row !== null && typeof row === 'object' && !Array.isArray(row),
    )
    : []
  const powerParameters =
    familyResult?.family === 'power_analysis' &&
    familyResult.parameters &&
    typeof familyResult.parameters === 'object'
      ? familyResult.parameters as Record<string, unknown>
      : null

  const hasEstimates = estimates.length > 0
  const compactJobId = jobId.length > 16 ? `${jobId.slice(0, 8)}…${jobId.slice(-6)}` : jobId

  const handleExportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `advanced-result-${jobId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [result, jobId])

  const [exporting, setExporting] = useState(false)
  const handleExportBundle = useCallback(
    async (includeData: boolean) => {
      setExporting(true)
      try {
        await downloadWithSession(
          advancedAnalysisExportUrl(jobId, includeData),
          `advanced-result-${jobId}.zip`,
        )
      } finally {
        setExporting(false)
      }
    },
    [jobId],
  )

  const summaryStats = useMemo(() => {
    if (!sampleFlow) return null
    const entries = Object.entries(sampleFlow).filter(
      ([, v]) => typeof v === 'number' || typeof v === 'string'
    )
    return entries.length > 0 ? entries : null
  }, [sampleFlow])

  return (
    <section className="adv-result-panel" aria-label="分析结果">
      {/* Header */}
      <AdvancedResultHeader
        capability={capability}
        jobId={jobId}
        compactJobId={compactJobId}
        onNewAnalysis={onNewAnalysis}
        onExportJson={handleExportJson}
        exporting={exporting}
        onExportBundle={handleExportBundle}
      />

      {/* Warnings */}
      {warnings.length > 0 && (
        <section className="adv-result-warnings" aria-label="分析警告">
          <h3>方法警告（{warnings.length}）</h3>
          <ul>
            {warnings.map(w => (
              <li
                key={`${w.code}:${w.message}`}
                className={`adv-warning-item severity-${w.severity || 'warning'}`}
              >
                <span className="adv-warning-code">{w.code}</span>
                <span className="adv-warning-msg">{w.message}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* APA Reports */}
      {apaReports.length > 0 && (
        <div className="adv-result-section">
          <div className="adv-section-title-row">
            <h3>解释性报告</h3>
            <span className="adv-language-tag">英文期刊写作 · APA 7th</span>
          </div>
          <blockquote className="adv-apa-report">
            {apaReports.map(report => (
              <p key={report}>{report}</p>
            ))}
          </blockquote>
        </div>
      )}

      <EmmConfidencePlot rows={estimatedMarginalMeans} />

      {/* Sample flow */}
      {summaryStats && (
        <div className="adv-result-section">
          <h3>样本流</h3>
          <div className="adv-sample-grid">
            {summaryStats.map(([key, value]) => (
              <div key={key} className="adv-sample-card">
                <span className="adv-sample-label">{key}</span>
                <strong className="adv-sample-value">{String(value)}</strong>
              </div>
            ))}
          </div>
        </div>
      )}

      {familyResult?.family === 'power_analysis' && (
        <section className="adv-result-section" aria-label="解析功效摘要">
          <h3>解析功效摘要</h3>
          <div className="adv-sample-grid">
            <div className="adv-sample-card">
              <span className="adv-sample-label">解算目标</span>
              <strong className="adv-sample-value">
                {powerSolveLabel(familyResult.solveFor)}
              </strong>
            </div>
            <div className="adv-sample-card">
              <span className="adv-sample-label">结果</span>
              <strong className="adv-sample-value">
                {formatNumber(
                  typeof familyResult.solvedValue === 'number'
                    ? familyResult.solvedValue
                    : null,
                )}
                {powerParameters?.solvedValueMetric === 'r_squared_change' ? ' (R² change)' : ''}
              </strong>
            </div>
            <div className="adv-sample-card">
              <span className="adv-sample-label">回代功效</span>
              <strong className="adv-sample-value">
                {formatPower(familyResult.achievedPower)}
              </strong>
            </div>
          </div>
        </section>
      )}

      {/* Estimates table */}
      {hasEstimates && <EstimatesTable estimates={estimates} />}

      {/* Family-specific result */}
      {familyResult && (
        <>
          <MethodResultVisuals familyResult={familyResult} />
          <FamilyResultTables familyResult={familyResult} />
          <div className="adv-result-section">
            <h3>详细结果</h3>
            <details className="adv-spec-detail">
            <summary>展开完整结果</summary>
            <pre className="adv-spec-pre">
              {JSON.stringify(familyResult, null, 2)}
            </pre>
            </details>
          </div>
        </>
      )}

      {/* Provenance */}
      {provenance && (
        <div className="adv-result-section adv-provenance-section">
          <h3>来源信息</h3>
          <dl className="adv-spec-dl">
            {Object.entries(provenance).map(([key, value]) => (
              <div key={key}>
                <dt>{key}</dt>
                <dd><code>{typeof value === 'object' ? JSON.stringify(value) : String(value)}</code></dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {/* Raw JSON */}
      <div className="adv-result-section">
        <details className="adv-spec-detail">
          <summary>查看原始 JSON</summary>
          <pre className="adv-spec-pre">
            {JSON.stringify(result, null, 2)}
          </pre>
        </details>
      </div>
    </section>
  )
}
