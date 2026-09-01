import type { AdvancedAnalysisCapability } from '../../types'

export interface Estimate {
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

export interface Warning {
  code: string
  severity?: 'info' | 'warning' | 'error'
  message: string
}

export interface SampleFlow {
  [key: string]: unknown
}

export function formatNumber(value: number | null | undefined, decimals = 4): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(decimals)
}

export function formatPValue(p: number | null | undefined): string {
  if (p === null || p === undefined) return '—'
  if (p < 0.001) return '< .001'
  return p.toFixed(4)
}

export function formatPower(value: unknown): string {
  return typeof value === 'number' ? `${(value * 100).toFixed(1)}%` : '—'
}

export function powerSolveLabel(value: unknown): string {
  if (value === 'sample_size') return '建议总样本量'
  if (value === 'power') return '回代功效'
  if (value === 'effect_size') return '最小可检测效应'
  return '解算结果'
}

interface AdvancedResultHeaderProps {
  capability: AdvancedAnalysisCapability
  jobId: string
  compactJobId: string
  onNewAnalysis: () => void
  onExportJson: () => void
  exporting: boolean
  onExportBundle: (includeData: boolean) => void
}

export function AdvancedResultHeader({
  capability,
  jobId,
  compactJobId,
  onNewAnalysis,
  onExportJson,
  exporting,
  onExportBundle,
}: AdvancedResultHeaderProps) {
  return (
    <div className="adv-result-header">
      <div>
        <p className="eyebrow">分析完成</p>
        <h2>{capability.label} — 结果</h2>
        <details className="adv-run-identity">
          <summary>运行记录 · <code>{compactJobId}</code></summary>
          {compactJobId !== jobId ? <code>{jobId}</code> : null}
        </details>
      </div>
      <div className="adv-result-actions">
        <button type="button" className="adv-btn-secondary" onClick={onExportJson}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <path d="M2 11v2a1 1 0 001 1h10a1 1 0 001-1v-2M8 2v9M5 8l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          导出 JSON
        </button>
        <button
          type="button"
          className="adv-btn-secondary"
          disabled={exporting}
          onClick={() => {
            void onExportBundle(false)
          }}
        >
          {exporting ? '正在导出…' : '导出论文复现包'}
        </button>
        <button
          type="button"
          className="adv-btn-secondary"
          disabled={exporting}
          onClick={() => {
            void onExportBundle(true)
          }}
        >
          {exporting ? '正在导出…' : '导出复现包（含数据）'}
        </button>
        <button type="button" className="adv-btn-primary" onClick={onNewAnalysis}>
          新建分析
        </button>
      </div>
    </div>
  )
}

interface EstimatesTableProps {
  estimates: Estimate[]
}

export function EstimatesTable({ estimates }: EstimatesTableProps) {
  return (
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
  )
}
