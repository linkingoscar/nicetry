import { useCallback, useEffect, useState } from 'react'
import './advanced.css'
import './advanced-extra.css'
import type { AdvancedAnalysisCapability } from '../../types'
import type { AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'
import type { DatasetVariableItem } from './DatasetVariablePicker'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { getAdvancedAnalysisStatus, getAdvancedAnalysisResult } from '../../api/advanced'
import { CapabilityList } from './CapabilityList'
import { AnalysisWizard } from './AnalysisWizard'
import { JobProgress } from './JobProgress'
import { AdvancedResultView } from './AdvancedResultView'

const STORAGE_KEY = 'researchpath_advanced_state'

type ManagerView =
  | { kind: 'list' }
  | { kind: 'wizard'; capability: AdvancedAnalysisCapability }
  | { kind: 'running'; capability: AdvancedAnalysisCapability; job: AdvancedJobResponse }
  | { kind: 'result'; capability: AdvancedAnalysisCapability; result: AdvancedResultResponse; job: AdvancedJobResponse }

interface AdvancedAnalysisManagerProps {
  datasetId?: string
  variables: DatasetVariableItem[]
  constructs: Array<{ id: string; label: string; itemIds: string[] }>
  allowedFamilies?: string[]
  catalogTitle?: string
  catalogDescription?: string
  context?: ResolvedAnalysisContext | null
}

function saveState(runId: string, family: string, capabilityLabel: string) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ runId, family, label: capabilityLabel }))
  } catch { /* quota exceeded — ignore */ }
}

function clearState() {
  localStorage.removeItem(STORAGE_KEY)
}

export function AdvancedAnalysisManager({
  datasetId,
  variables,
  constructs,
  allowedFamilies,
  catalogTitle,
  catalogDescription,
  context = null,
}: AdvancedAnalysisManagerProps) {
  const [view, setView] = useState<ManagerView>({ kind: 'list' })
  const [recovering, setRecovering] = useState(true)

  /* Recover running/completed jobs from previous session */
  useEffect(() => {
    let active = true
    const recover = async () => {
      try {
        const saved = localStorage.getItem(STORAGE_KEY)
        if (!saved) return
        const { runId, family, label } = JSON.parse(saved)
        if (!runId || !family) return
        if (allowedFamilies && !allowedFamilies.includes(family)) {
          clearState()
          return
        }
        const job = await getAdvancedAnalysisStatus(runId)
        const cap: AdvancedAnalysisCapability = {
          family,
          label: label || family,
          status: 'experimental',
          specVersion: '0.1.0',
          resultVersion: '0.1.0',
          plannedEngine: 'R',
          minimumValidation: [],
          executionAvailable: true,
          slices: [],
        }
        if (!active) return
        if (job.status === 'succeeded') {
          try {
            const result = await getAdvancedAnalysisResult(runId)
            setView({ kind: 'result', capability: cap, result, job })
          } catch {
            setView({ kind: 'running', capability: cap, job })
          }
        } else if (job.status === 'queued' || job.status === 'running' || job.status === 'cancelling') {
          setView({ kind: 'running', capability: cap, job })
        } else {
          clearState()
        }
      } catch {
        clearState()
      } finally {
        if (active) setRecovering(false)
      }
    }
    recover()
    return () => { active = false }
  }, [allowedFamilies])

  useEffect(() => {
    if (!recovering) return
    const timeout = setTimeout(() => setRecovering(false), 2000)
    return () => clearTimeout(timeout)
  }, [recovering])

  const handleSelect = useCallback((cap: AdvancedAnalysisCapability) => {
    setView({ kind: 'wizard', capability: cap })
  }, [])

  const handleJobStarted = useCallback((cap: AdvancedAnalysisCapability, job: AdvancedJobResponse) => {
    saveState(job.id, cap.family, cap.label)
    setView({ kind: 'running', capability: cap, job })
  }, [])

  const handleJobComplete = useCallback((cap: AdvancedAnalysisCapability, job: AdvancedJobResponse, result?: AdvancedResultResponse) => {
    if (result) {
      setView({ kind: 'result', capability: cap, result, job })
    } else {
      clearState()
      setView({ kind: 'list' })
    }
  }, [])

  const handleBack = useCallback(() => {
    clearState()
    setView({ kind: 'list' })
  }, [])

  if (recovering) {
    return (
      <div className="adv-main" aria-live="polite">
        <div className="adv-loading-state">
          <div className="adv-spinner" />
          <p>正在恢复高级分析状态...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="adv-main">
      {view.kind !== 'list' && (
        <nav className="adv-breadcrumb" aria-label="高级分析导航">
          <button type="button" className="adv-back-btn" onClick={handleBack}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
              <path d="M10 12L6 8l4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            返回方法列表
          </button>
          <span className="adv-breadcrumb-current">{view.capability.label}</span>
        </nav>
      )}

      {view.kind === 'list' && (
        <CapabilityList
          onSelect={handleSelect}
          hasDataset={Boolean(datasetId)}
          allowedFamilies={allowedFamilies}
          title={catalogTitle}
          description={catalogDescription}
        />
      )}

      {view.kind === 'wizard' && (
        <AnalysisWizard
          capability={view.capability}
          datasetId={datasetId}
          variables={variables}
          constructs={constructs}
          context={context}
          onJobStarted={(job) => handleJobStarted(view.capability, job)}
        />
      )}

      {view.kind === 'running' && (
        <JobProgress
          jobId={view.job.id}
          initialJob={view.job}
          capability={view.capability}
          onComplete={(job, result) => handleJobComplete(view.capability, job, result)}
          onCancel={handleBack}
        />
      )}

      {view.kind === 'result' && (
        <AdvancedResultView
          result={view.result}
          capability={view.capability}
          jobId={view.job.id}
          onNewAnalysis={handleBack}
        />
      )}
    </div>
  )
}
