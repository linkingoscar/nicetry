import type { FC } from 'react'
import { analysisExportUrl } from '../../api'
import { downloadWithSession } from '../../api/client'
import type { AnalysisJob, ModelSpec, ModelValidation } from '../../types'
import styles from './ModelBuilderSidebar.module.css'

interface ModelBuilderSidebarProps {
  model: ModelSpec
  validation: ModelValidation | null
  freezeMutation: {
    data?: { version: number; modelHash: string } | null
    isPending: boolean
    error?: Error | null
    mutate: () => void
  }
  overrideReason: string
  setOverrideReason: (val: string) => void
  contextGateBlocked: boolean
  contextBindingStale: boolean
  analysisRunning: boolean
  analysisMutation: { error?: Error | null; mutate: (arg?: undefined) => void }
  analysisJob?: AnalysisJob | null
  cancelMutation: { isPending: boolean; mutate: () => void }
}

export const ModelBuilderSidebar: FC<ModelBuilderSidebarProps> = ({
  model,
  validation,
  freezeMutation,
  overrideReason,
  setOverrideReason,
  contextGateBlocked,
  contextBindingStale,
  analysisRunning,
  analysisMutation,
  analysisJob,
  cancelMutation,
}) => {
  return (
    <aside className="model-sidebar model-sidebar-right" aria-label="模型检查与运行">
      <div className="section-heading">
        <div>
          <p className="eyebrow">预运行校验</p>
          <h2>检查与运行</h2>
        </div>
      </div>

      <p className="muted">先在编辑区配置模型，再确认检查结果。冻结保存本次规格，运行只使用该版本。</p>
      {!validation ? <p role="status">正在保存并检查当前设置…</p> : null}
      {freezeMutation.error || analysisMutation.error ? <p role="alert" className="validation-error">{freezeMutation.error?.message ?? analysisMutation.error?.message}</p> : null}
      {(validation?.warnings ?? []).map((warning) => (
        <div key={warning.code} className="validation-warning">
          ⚠️ {warning.message}
        </div>
      ))}

      {(validation?.errors ?? []).map((error) => (
        <div key={error} className="validation-error">
          ❌ {error}
        </div>
      ))}

      {validation?.valid ? (
        <div className={`validation-summary ${validation.executionAvailable ? 'is-valid' : 'is-pending'}`}>
          <span>估计模式：{model.estimation.family === 'sem' ? 'lavaan (SEM)' : 'PROCESS (OLS)'}</span>
          {validation.unsupportedReason ? <small>{validation.unsupportedReason}</small> : null}
        </div>
      ) : null}

      {freezeMutation.data ? (
        <div className="frozen-banner">
          <strong>已冻结 Version {freezeMutation.data.version}</strong>
          <code>{freezeMutation.data.modelHash}</code>
        </div>
      ) : (
        <div className={styles.freezeControls}>
          {validation?.valid && validation.warnings.length > 0 ? (
            <input
              type="text"
              value={overrideReason}
              onChange={(event) => setOverrideReason(event.target.value)}
              aria-label="方法警告的处理与解释边界"
              placeholder="记录方法警告的处理与解释边界"
              className={styles.overrideInput}
            />
          ) : null}
          <button
            type="button"
            className="secondary-button"
            disabled={
              !validation?.valid
              || (validation.warnings.length > 0 && !overrideReason.trim())
              || freezeMutation.isPending
              || contextGateBlocked
              || contextBindingStale
            }
            onClick={() => freezeMutation.mutate()}
          >
            {freezeMutation.isPending ? '冻结中...' : '冻结并确定模型版本'}
          </button>
        </div>
      )}

      <button
        type="button"
        className="run-button"
        disabled={contextGateBlocked || contextBindingStale || !validation?.executionAvailable || !freezeMutation.data || analysisRunning}
        onClick={() => analysisMutation.mutate(undefined)}
      >
        {analysisRunning
          ? '分析中...'
          : validation?.executionAvailable ? '运行模型分析与估计' : '当前模型暂未开放估计'}
      </button>

      {analysisRunning ? (
        <div className="analysis-progress" role="status" aria-live="polite">
          <div>
            <strong>{analysisJob?.status === 'running' ? '后端正在计算中…' : '排队中…'}</strong>
            <span>{Math.round((analysisJob?.progress ?? 0) * 100)}%</span>
          </div>
          <progress value={analysisJob?.progress ?? 0} max={1} />
          <small>{analysisJob?.error ?? '请稍候，处理完成后自动展示分析报告。'}</small>
          <button
            type="button"
            className="text-button"
            disabled={cancelMutation.isPending || analysisJob?.status === 'cancelling'}
            onClick={() => cancelMutation.mutate()}
          >
            {cancelMutation.isPending || analysisJob?.status === 'cancelling' ? '正在取消…' : '取消分析'}
          </button>
        </div>
      ) : null}

      {analysisJob?.status === 'failed' || analysisJob?.status === 'cancelled' ? (
        <p className="validation-error" role="alert">
          {analysisJob.error ?? (analysisJob.status === 'cancelled' ? '分析任务已取消。' : '模型分析运行失败，请检查数据。')}
        </p>
      ) : null}

      {analysisJob?.status === 'succeeded' ? (
        <div className={`export-actions ${styles.exportActions}`}>
          <button
            type="button"
            className={`secondary-button ${styles.exportButton}`}
            onClick={() => {
              void downloadWithSession(
                analysisExportUrl(analysisJob.id, false),
                `analysis-result-${analysisJob.id}.zip`,
              )
            }}
          >
            下载结果与复现包
          </button>
          <button
            type="button"
            className={`secondary-button ${styles.exportButton}`}
            onClick={() => {
              void downloadWithSession(
                analysisExportUrl(analysisJob.id, true),
                `analysis-export-${analysisJob.id}.zip`,
              )
            }}
          >
            下载结果包（含数据）
          </button>
        </div>
      ) : null}
    </aside>
  )
}
