import { useEffect, useRef, useState, useCallback } from 'react'
import type { AdvancedAnalysisCapability } from '../../types'
import type { AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'
import { getAdvancedAnalysisStatus, getAdvancedAnalysisResult, cancelAdvancedAnalysis } from '../../api/advanced'

interface JobProgressProps {
  jobId: string
  initialJob: AdvancedJobResponse
  capability: AdvancedAnalysisCapability
  onComplete: (job: AdvancedJobResponse, result?: AdvancedResultResponse) => void
  onCancel: () => void
}

const STAGE_LABELS: Record<string, string> = {
  queued: '排队等待',
  preparing_data: '准备数据',
  validate_spec: '验证规格',
  load_dataset: '加载数据集',
  prepare_input: '准备输入',
  run_engine: '运行 R 引擎',
  validate_result: '验证结果',
  persist_result: '持久化结果',
  succeeded: '完成',
  cancelling: '正在取消...',
  cancelled: '已取消',
  failed: '失败',
  running: '运行中',
}

export function JobProgress({ jobId, initialJob, capability, onComplete, onCancel }: JobProgressProps) {
  const [job, setJob] = useState<AdvancedJobResponse>(initialJob)
  const [error, setError] = useState<string | null>(null)
  const [isCancelling, setIsCancelling] = useState(false)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const pollingRef = useRef<number | null>(null)
  const startTimeRef = useRef(Date.now())
  const retryCountRef = useRef(0)

  /* Elapsed timer */
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000))
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  /* Polling for status */
  useEffect(() => {
    let mounted = true
    const controller = new AbortController()

    const fetchStatus = async () => {
      try {
        const currentJob = await getAdvancedAnalysisStatus(jobId, controller.signal)
        if (!mounted) return

        retryCountRef.current = 0
        setJob(currentJob)

        if (currentJob.status === 'succeeded') {
          try {
            const res = await getAdvancedAnalysisResult(jobId, controller.signal)
            if (!mounted) return
            onComplete(currentJob, res)
          } catch (err: unknown) {
            const e = err as { message?: string }
            setError(`获取结果失败：${e.message || '未知错误'}`)
          }
        } else if (currentJob.status === 'failed') {
          setError(currentJob.error || '分析运行失败')
        } else if (currentJob.status === 'cancelled') {
          onCancel()
        } else {
          // Still running or queued, poll again
          pollingRef.current = window.setTimeout(fetchStatus, 1500)
        }
      } catch (err: unknown) {
        if (mounted && !controller.signal.aborted) {
          const e = err as { message?: string }
          // 网络抖动/瞬时 5xx：有限重试并退避，不把瞬时故障误判为任务终态。
          retryCountRef.current += 1
          if (retryCountRef.current <= 5) {
            pollingRef.current = window.setTimeout(fetchStatus, 1500 * retryCountRef.current)
          } else {
            setError(`状态查询失败：${e.message || '未知错误'}`)
          }
        }
      }
    }

    if (job.status === 'running' || job.status === 'queued' || job.status === 'cancelling') {
      pollingRef.current = window.setTimeout(fetchStatus, 1500)
    }

    return () => {
      mounted = false
      if (pollingRef.current) clearTimeout(pollingRef.current)
      controller.abort()
    }
  }, [jobId, onComplete, onCancel, job.status]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleCancel = useCallback(async () => {
    setIsCancelling(true)
    try {
      await cancelAdvancedAnalysis(jobId)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(`取消失败：${e.message || '未知错误'}`)
      setIsCancelling(false)
    }
  }, [jobId])

  const progressPercent = Math.round(job.progress * 100)
  const stageLabel = STAGE_LABELS[job.stage] || job.stage
  const isActive = job.status === 'running' || job.status === 'queued' || job.status === 'cancelling'

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60)
    const s = seconds % 60
    return m > 0 ? `${m}分${s.toString().padStart(2, '0')}秒` : `${s}秒`
  }

  return (
    <section className="adv-progress-panel" aria-label="分析进度">
      <div className="adv-progress-header">
        <div className="adv-progress-title-row">
          <h2>{capability.label}</h2>
          {isActive && <span className="adv-live-dot" aria-hidden="true" />}
        </div>
        <p className="muted">任务 ID: <code>{jobId}</code></p>
      </div>

      {/* Main progress */}
      <div className="adv-progress-body">
        <div className="adv-progress-visual">
          <div className="adv-progress-bar-wrap">
            <div
              className={`adv-progress-bar ${isActive ? 'is-active' : ''}`}
              style={{ width: `${progressPercent}%` }}
              role="progressbar"
              aria-valuenow={progressPercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`分析进度 ${progressPercent}%`}
            />
          </div>
          <div className="adv-progress-meta">
            <span className="adv-progress-percent">{progressPercent}%</span>
            <span className="adv-progress-elapsed">{formatTime(elapsedSeconds)}</span>
          </div>
        </div>

        {/* Stage info */}
        <div className="adv-progress-stage" role="status" aria-live="polite" aria-atomic="true">
          <div className="adv-stage-current">
            <span className="adv-stage-label">当前阶段</span>
            <strong>{stageLabel}</strong>
          </div>
          <div className="adv-stage-status">
            <span className="adv-stage-label">状态</span>
            <span className={`adv-status-chip status-${job.status}`}>
              {job.status === 'queued' ? '排队中' :
               job.status === 'running' ? '运行中' :
               job.status === 'cancelling' ? '取消中' :
               job.status === 'succeeded' ? '已完成' :
               job.status === 'failed' ? '失败' :
               job.status === 'cancelled' ? '已取消' : job.status}
            </span>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="adv-error-banner" role="alert">
          <strong>分析{job.status === 'failed' ? '失败' : '异常'}</strong>
          <p>{error}</p>
          {job.errorCode ? <code className="adv-error-code">{job.errorCode}</code> : null}
          {job.remediation ? (
            <p className="adv-error-remediation"><strong>建议：</strong>{job.remediation}</p>
          ) : null}
        </div>
      )}

      {/* Actions */}
      <div className="adv-progress-actions">
        {isActive && !isCancelling && (
          <button
            type="button"
            className="adv-btn-danger"
            onClick={handleCancel}
            disabled={isCancelling}
          >
            取消分析
          </button>
        )}
        {isCancelling && (
          <span className="adv-cancelling-label" aria-live="assertive">
            <span className="adv-btn-spinner" aria-hidden="true" />
            正在取消...
          </span>
        )}
        {error && (
          <button type="button" className="adv-btn-secondary" onClick={onCancel}>
            返回
          </button>
        )}
      </div>
    </section>
  )
}
