import type React from 'react'
import type { AdvancedAnalysisCapability } from '../../types'

export interface ValidationSummaryProps {
  spec: Record<string, unknown>
  capability: AdvancedAnalysisCapability
  warnings?: Array<{ code: string; severity: 'info' | 'warning' | 'error'; message: string }>
  datasetVersionId?: string
  sampleCounts?: {
    participants?: number
    rows?: number
    clusters?: number
    waves?: number
  }
}

export const ValidationSummary: React.FC<ValidationSummaryProps> = ({
  spec,
  capability,
  warnings = [],
  datasetVersionId,
  sampleCounts,
}) => {
  const estimand = (spec.estimandSpec || {}) as Record<string, unknown>
  const activeSlice = capability.slices?.find(s => s.executionAvailable) || capability.slices?.[0]

  return (
    <div className="adv-validation-summary-card" data-testid="validation-summary">
      <div className="adv-valid-banner" role="status">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <circle cx="10" cy="10" r="9" stroke="currentColor" strokeWidth="2" />
          <path d="M6 10l3 3 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span>规格校验完成且逻辑有效</span>
      </div>

      {/* Warnings List */}
      {warnings.length > 0 && (
        <div className="adv-summary-section">
          <h4>分析警告与风险提示 ({warnings.length})</h4>
          <ul className="adv-warnings-list" aria-label="验证警告">
            {warnings.map(w => (
              <li key={`${w.code}:${w.message}`} className={`adv-warning-item severity-${w.severity}`}>
                <span className="adv-warning-code">{w.code}</span>
                <span className="adv-warning-msg">{w.message}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 3-Axis Status Badges */}
      <div className="adv-summary-section">
        <h4>能力评估与三轴状态 (Status Axes)</h4>
        <div className="adv-status-axes-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
          <div className="adv-status-badge">
            <span className="adv-badge-label">工程实现轴 (Engineering)</span>
            <strong className="adv-badge-value">{activeSlice?.executionAvailable ? 'available' : 'planned'}</strong>
          </div>
          <div className="adv-status-badge">
            <span className="adv-badge-label">自动证据轴 (Evidence)</span>
            <strong className="adv-badge-value">{capability.minimumValidation.length > 0 ? 'declared' : 'partial'}</strong>
          </div>
          <div className="adv-status-badge">
            <span className="adv-badge-label">发布状态轴 (Release)</span>
            <strong className="adv-badge-value">{activeSlice?.status || capability.status}</strong>
          </div>
        </div>
      </div>

      {/* Estimand and Unit Counts */}
      <div className="adv-summary-section">
        <h4>Estimand 与分析单元定义</h4>
        <dl className="adv-spec-dl">
          <div>
            <dt>分析目标 (Role)</dt>
            <dd>{(estimand.analysisRole as string) || '未指定 (UNSPECIFIED_ROLE)'}</dd>
          </div>
          <div>
            <dt>因果防伪目标</dt>
            <dd>{estimand.causalTarget ? '是 (Causal Target)' : '否 (Descriptive / Observational)'}</dd>
          </div>
          <div>
            <dt>分析单位 (Unit)</dt>
            <dd>{(estimand.analysisUnit as string) || '未指定 (UNSPECIFIED_UNIT)'}</dd>
          </div>
          <div>
            <dt>效应尺度 (Scale)</dt>
            <dd>{(estimand.effectScale as string) || '原始尺度 (raw)'}</dd>
          </div>
          <div>
            <dt>数据集版本</dt>
            <dd><code>{datasetVersionId || (spec.datasetVersionId as string) || '默认当前版本'}</code></dd>
          </div>
          <div>
            <dt>样本结构基数</dt>
            <dd>
              {sampleCounts ? (
                <span>
                  被试: {sampleCounts.participants ?? '—'} | 记录: {sampleCounts.rows ?? '—'} | 聚类: {sampleCounts.clusters ?? '—'} | 波次: {sampleCounts.waves ?? '—'}
                </span>
              ) : (
                '解析中 (N/A)'
              )}
            </dd>
          </div>
        </dl>
      </div>

      {/* Resolved Slice & Limitations */}
      <div className="adv-summary-section">
        <h4>引擎切片与已知限制</h4>
        <dl className="adv-spec-dl">
          <div>
            <dt>解析 Capability ID</dt>
            <dd><code>{activeSlice?.id || capability.family}</code></dd>
          </div>
          <div>
            <dt>运行算法引擎</dt>
            <dd><code>{activeSlice?.executionAvailable ? 'R Execution Engine Available' : 'Planned Engine (拒绝计算)'}</code></dd>
          </div>
          <div>
            <dt>已知界限/拒绝条件</dt>
            <dd>{activeSlice?.supportBoundary || '无特殊界限声明'}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}
