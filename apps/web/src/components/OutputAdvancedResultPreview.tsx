import type { AdvancedResultResponse } from '../types/advanced'
import { FamilyResultTables } from './advanced/FamilyResultTables'
import { MethodResultVisuals } from './advanced/MethodResultVisuals'
import {
  EstimatesTable,
  type Estimate,
  type Warning,
} from './advanced/AdvancedResultViewSections'

interface OutputAdvancedResultPreviewProps {
  label: string
  runId: string
  result: AdvancedResultResponse
}

export function OutputAdvancedResultPreview({ label, runId, result }: OutputAdvancedResultPreviewProps) {
  const bundle = result as Record<string, unknown>
  const warnings = (bundle.warnings ?? []) as Warning[]
  const estimates = (bundle.estimates ?? []) as Estimate[]
  const familyResult = (bundle.familyResult ?? null) as Record<string, unknown> | null
  const apaReports = (bundle.apaReports ?? []) as string[]

  return (
    <section className="adv-result-panel" aria-label={`${label}只读结果`}>
      <div className="adv-result-header">
        <div>
          <p className="eyebrow">只读结果</p>
          <h2>{label} · 本次结果</h2>
          <p className="muted">运行 {runId}</p>
        </div>
      </div>

      {warnings.length ? (
        <section className="adv-result-warnings" aria-label="分析警告">
          <h3>方法警告（{warnings.length}）</h3>
          <ul>
            {warnings.map((warning) => (
              <li key={`${warning.code}:${warning.message}`} className={`adv-warning-item severity-${warning.severity ?? 'warning'}`}>
                <span className="adv-warning-code">{warning.code}</span>
                <span className="adv-warning-msg">{warning.message}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {apaReports.length ? (
        <section className="adv-result-section">
          <h3>解释性报告</h3>
          <blockquote className="adv-apa-report">
            {apaReports.map((report) => <p key={report}>{report}</p>)}
          </blockquote>
        </section>
      ) : null}

      {estimates.length ? <EstimatesTable estimates={estimates} /> : null}
      {familyResult ? (
        <>
          <MethodResultVisuals familyResult={familyResult} />
          <FamilyResultTables familyResult={familyResult} />
        </>
      ) : null}

      <details className="adv-spec-detail">
        <summary>查看完整只读结果</summary>
        <pre className="adv-spec-pre">{JSON.stringify(result, null, 2)}</pre>
      </details>
    </section>
  )
}
