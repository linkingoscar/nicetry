import { useQuery } from '@tanstack/react-query'

import { getAnalysisJob, getAnalysisResult } from '../api/analyses'
import { getAdvancedAnalysisResult, getAdvancedAnalysisStatus } from '../api/advanced'
import type { RegisteredOutputRun } from './analyses/outputRunRegistry'
import { OutputAdvancedResultPreview } from './OutputAdvancedResultPreview'
import { ResultPanel } from './ResultPanel'

interface OutputRegisteredRunDetailProps {
  run: RegisteredOutputRun
  onClose: () => void
  isPrimary?: boolean
  onTogglePrimary?: () => void
}

const TERMINAL = new Set(['succeeded', 'failed', 'cancelled'])

function statusLabel(status?: string) {
  if (status === 'queued') return '排队中'
  if (status === 'running') return '运行中'
  if (status === 'cancelling') return '取消中'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'cancelled') return '已取消'
  return '正在读取服务端状态'
}

export function OutputRegisteredRunDetail({
  run,
  onClose,
  isPrimary = false,
  onTogglePrimary,
}: OutputRegisteredRunDetailProps) {
  const modelStatus = useQuery({
    queryKey: ['output-model-run-status', run.runId],
    queryFn: () => getAnalysisJob(run.runId),
    enabled: run.source === 'model',
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && TERMINAL.has(status) ? false : 1_000
    },
  })
  const advancedStatus = useQuery({
    queryKey: ['output-advanced-run-status', run.runId],
    queryFn: ({ signal }) => getAdvancedAnalysisStatus(run.runId, signal),
    enabled: run.source === 'advanced',
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && TERMINAL.has(status) ? false : 1_000
    },
  })

  const status = run.source === 'model' ? modelStatus.data?.status : advancedStatus.data?.status
  const statusError = run.source === 'model' ? modelStatus.error : advancedStatus.error
  const jobError = run.source === 'model' ? modelStatus.data?.error : advancedStatus.data?.error

  const modelResult = useQuery({
    queryKey: ['output-model-run-result', run.runId],
    queryFn: () => getAnalysisResult(run.runId),
    enabled: run.source === 'model' && status === 'succeeded',
    retry: false,
    staleTime: Infinity,
  })
  const advancedResult = useQuery({
    queryKey: ['output-advanced-run-result', run.runId],
    queryFn: ({ signal }) => getAdvancedAnalysisResult(run.runId, signal),
    enabled: run.source === 'advanced' && status === 'succeeded',
    retry: false,
    staleTime: Infinity,
  })

  return (
    <section className="context-catalog" aria-label="模型或高级运行详情">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">服务端运行</p>
          <h2>{run.label}</h2>
          <p className="muted">{new Date(run.createdAt).toLocaleString()} · {statusLabel(status)}</p>
        </div>
        <button type="button" className="secondary-button" onClick={onClose}>关闭详情</button>
      </div>
      <div className="method-card-status-row">
        <span className="context-method-status">运行 {run.runId.slice(0, 12)}</span>
        <span className="context-method-status">{run.source === 'model' ? 'PROCESS / SEM' : '结构化高级分析'}</span>
        {status ? <span className="context-method-status">服务端已确认</span> : null}
        {isPrimary ? <span className="context-method-status">主要结果</span> : null}
      </div>

      {onTogglePrimary ? (
        <div className="method-card-actions">
          <button type="button" className="secondary-button" onClick={onTogglePrimary}>
            {isPrimary ? '取消主要结果' : '设为主要结果'}
          </button>
        </div>
      ) : null}

      {statusError ? (
        <p className="validation-error" role="alert">无法读取该运行：{statusError.message}</p>
      ) : null}
      {jobError ? <p className="validation-error" role="alert">{jobError}</p> : null}
      {!status && !statusError ? <p role="status">正在从服务端读取任务状态…</p> : null}

      {run.source === 'model' && modelResult.isLoading ? <p role="status">正在加载模型结果…</p> : null}
      {run.source === 'advanced' && advancedResult.isLoading ? <p role="status">正在加载分析结果…</p> : null}
      {modelResult.error ? <p className="validation-error" role="alert">模型结果加载失败：{modelResult.error.message}</p> : null}
      {advancedResult.error ? <p className="validation-error" role="alert">高级分析结果加载失败：{advancedResult.error.message}</p> : null}

      {run.source === 'model' && modelResult.data ? (
        <ResultPanel result={modelResult.data} isRunning={false} title={`${run.label} · 本次结果`} />
      ) : null}
      {run.source === 'advanced' && advancedResult.data ? (
        <OutputAdvancedResultPreview label={run.label} runId={run.runId} result={advancedResult.data} />
      ) : null}
    </section>
  )
}
