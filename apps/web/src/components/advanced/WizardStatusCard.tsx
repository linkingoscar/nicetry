import type { AdvancedAnalysisCapability, AdvancedAnalysisSpec } from '../../types'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'

export interface ValidationResult {
  valid: boolean
  spec: AdvancedAnalysisSpec | null
  warnings: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  specHash?: string
}

interface WizardStatusCardProps {
  capability: AdvancedAnalysisCapability
  validationResult: ValidationResult
  draftId?: string | null
  context?: ResolvedAnalysisContext | null
  overrideReason: string
  setOverrideReason: (reason: string) => void
  submitError: string | null
  submitting: boolean
  onBackToConfig: () => void
  onSubmit: () => void
}

export function WizardStatusCard({
  capability,
  validationResult,
  draftId,
  context,
  overrideReason,
  setOverrideReason,
  submitError,
  submitting,
  onBackToConfig,
  onSubmit,
}: WizardStatusCardProps) {
  return (
    <div className="adv-wizard-panel">
      <div className="adv-panel-header">
        <h2>验证摘要</h2>
      </div>

      <div className="adv-validation-summary">
        <div className="adv-valid-banner" role="status">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2"/>
            <path d="M6 10l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
          <span>规格有效，可以提交运行</span>
        </div>

        {/* Warnings */}
        {validationResult.warnings.length > 0 && (
          <ul className="adv-warnings-list" aria-label="验证警告">
            {validationResult.warnings.map(w => (
              <li
                key={`${w.code}:${w.message}`}
                className={`adv-warning-item severity-${w.severity}`}
              >
                <span className="adv-warning-code">{w.code}</span>
                <span className="adv-warning-msg">{w.message}</span>
              </li>
            ))}
          </ul>
        )}

        {draftId && context ? (
          <div className="adv-role-override-note">
            <label htmlFor="adv-role-override-reason">
              角色覆盖理由（仅在修改结构默认绑定时必填）
            </label>
            <textarea
              id="adv-role-override-reason"
              className="adv-textarea"
              value={overrideReason}
              onChange={(event) => setOverrideReason(event.target.value)}
              placeholder="如果规格中的 subject / cluster / time / group 等角色不同于结构默认值，请说明数据来源和统计理由（至少 10 个字符）。"
              rows={3}
            />
          </div>
        ) : null}

        {/* Spec summary table */}
        <div className="adv-spec-summary">
          <h3>规格概要</h3>
          <dl className="adv-spec-dl">
            <div>
              <dt>方法族</dt>
              <dd><code>{capability.family}</code></dd>
            </div>
            <div>
              <dt>分析 ID</dt>
              <dd><code>{(validationResult.spec as Record<string, unknown>)?.analysisId as string || '—'}</code></dd>
            </div>
            <div>
              <dt>置信水平</dt>
              <dd><code>{(validationResult.spec as Record<string, unknown>)?.confidenceLevel as number || 0.95}</code></dd>
            </div>
            <div>
              <dt>随机种子</dt>
              <dd><code>{(validationResult.spec as Record<string, unknown>)?.seed as number || '—'}</code></dd>
            </div>
          </dl>
        </div>

        {/* Raw validated spec */}
        <details className="adv-spec-detail">
          <summary>查看完整验证后规格</summary>
          <pre className="adv-spec-pre">
            {JSON.stringify(validationResult.spec, null, 2)}
          </pre>
        </details>
      </div>

      {submitError && (
        <div className="adv-error-banner" role="alert">
          <strong>提交失败</strong>
          <p>{submitError}</p>
        </div>
      )}

      <div className="adv-wizard-actions">
        <button
          type="button"
          className="adv-btn-secondary"
          onClick={onBackToConfig}
        >
          返回编辑
        </button>
        <button
          type="button"
          className="adv-btn-primary"
          onClick={onSubmit}
          disabled={submitting}
        >
          {submitting ? (
            <><span className="adv-btn-spinner" aria-hidden="true" /> 提交中...</>
          ) : (
            '提交后台运行'
          )}
        </button>
      </div>
    </div>
  )
}
