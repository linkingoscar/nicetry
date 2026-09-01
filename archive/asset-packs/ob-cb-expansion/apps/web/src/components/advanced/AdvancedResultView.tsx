import { useCallback, useMemo } from 'react'
import type { AdvancedAnalysisCapability } from '../../types'
import type { ExtendedAdvancedResultResponse } from '../../types/advanced'
import { advancedAnalysisExportUrl } from '../../api/advanced'
import { EmmConfidencePlot } from './EmmConfidencePlot'
import { FamilyResultTables } from './FamilyResultTables'

interface AdvancedResultViewProps {
  result: ExtendedAdvancedResultResponse
  capability: AdvancedAnalysisCapability
  jobId: string
  onNewAnalysis: () => void
}

interface Estimate {
  id?: string
  label?: string
  estimate?: number
  standardError?: number
  statistic?: number
  pValue?: number | null
  degreesOfFreedom?: number | null
  confidenceLower?: number | null
  confidenceUpper?: number | null
  [key: string]: unknown
}

interface Warning {
  code: string
  severity?: 'info' | 'warning' | 'error'
  message: string
}

interface SampleFlow {
  [key: string]: unknown
}

function formatNumber(value: number | null | undefined, decimals = 4): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(decimals)
}

function formatPValue(p: number | null | undefined): string {
  if (p === null || p === undefined) return '—'
  if (p < 0.001) return '< .001'
  return p.toFixed(4)
}

function formatPower(value: unknown): string {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

function powerSolveLabel(value: unknown): string {
  if (value === 'sample_size') return '建议总样本量'
  if (value === 'power') return '回代功效'
  if (value === 'effect_size') return '最小可检测效应'
  return '解算结果'
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

  const handleExportJson = useCallback(() => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `advanced-result-${jobId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [result, jobId])

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
      <div className="adv-result-header">
        <div>
          <p className="eyebrow">分析完成</p>
          <h2>{capability.label} — 结果</h2>
          <p className="muted">任务 ID: <code>{jobId}</code></p>
        </div>
        <div className="adv-result-actions">
          <button type="button" className="adv-btn-secondary" onClick={handleExportJson}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2M8 2v9M5 8l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            导出 JSON
          </button>
          <a className="adv-btn-secondary" href={advancedAnalysisExportUrl(jobId)} download>
            导出论文复现包
          </a>
          <a className="adv-btn-secondary" href={advancedAnalysisExportUrl(jobId, true)} download>
            导出复现包（含数据）
          </a>
          <button type="button" className="adv-btn-primary" onClick={onNewAnalysis}>
            新建分析
          </button>
        </div>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <section className="adv-result-warnings" aria-label="分析警告">
          <h3>⚠ 警告 ({warnings.length})</h3>
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
          <h3>解释性报告 (APA)</h3>
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
      {hasEstimates && (
        <div className="adv-result-section">
          <h3>估计结果</h3>
          <div className="adv-table-wrap">
            <table className="adv-result-table" aria-label="参数估计">
              <thead>
                <tr>
                  <th>项</th>
                  <th>估计值</th>
                  <th>标准误</th>
                  <th>统计量</th>
                  <th>df</th>
                  <th>p 值</th>
                  <th>95% CI</th>
                </tr>
              </thead>
              <tbody>
                {estimates.map((est, idx) => (
                  <tr key={est.id ?? [est.label, est.estimate, est.standardError, est.pValue].join(':')}>
                    <td className="adv-est-term">{est.label || `项 ${idx + 1}`}</td>
                    <td className="adv-est-num">{formatNumber(est.estimate)}</td>
                    <td className="adv-est-num">{formatNumber(est.standardError)}</td>
                    <td className="adv-est-num">{formatNumber(est.statistic)}</td>
                    <td className="adv-est-num">{formatNumber(est.degreesOfFreedom, 2)}</td>
                    <td className="adv-est-num adv-est-p">{formatPValue(est.pValue)}</td>
                    <td className="adv-est-num">
                      {est.confidenceLower !== null && est.confidenceLower !== undefined &&
                      est.confidenceUpper !== null && est.confidenceUpper !== undefined
                        ? `[${formatNumber(est.confidenceLower)}, ${formatNumber(est.confidenceUpper)}]`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Family-specific result */}
      {familyResult && (
        <>
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
