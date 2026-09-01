import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createAnalysisDraft, getAnalysisDraftValidity } from '../../api/analysis-context'
import { useApplicableCapabilities } from '../../hooks/useApplicableCapabilities'
import type { ApplicableCapability, ResolvedAnalysisContext } from '../../types/analysis-context'
import type { DatasetVariable } from '../../types/datasets'
import type { AdvancedAnalysisCapability, AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'
import { ContextReadinessPanel } from './ContextReadinessPanel'
import { InvalidationNotice } from './InvalidationNotice'
import { AnalysisWizard } from '../advanced/AnalysisWizard'
import { JobProgress } from '../advanced/JobProgress'
import { AdvancedResultView } from '../advanced/AdvancedResultView'
import { ImputationPlanWorkspace } from './ImputationPlanWorkspace'
import {
  familyLabel,
  internalWorkbenchTarget,
  maturityLabel,
  publicationLabel,
  toWizardVariables,
  wizardCapability,
} from './contextCapabilityCatalogUtils'

import type { WorkbenchTarget } from './workbenchNavigation'

interface ContextCapabilityCatalogProps {
  context: ResolvedAnalysisContext
  variables?: DatasetVariable[]
  onNavigate?: (target: WorkbenchTarget) => void
  onPrepare?: () => void
}

const FAMILY_ORDER = ['empirical', 'model', 'questionnaire_measurement', 'experimental_design', 'multilevel_model', 'multiple_imputation', 'power_analysis']

export function ContextCapabilityCatalog({ context, variables = [], onNavigate, onPrepare }: ContextCapabilityCatalogProps) {
  const queryClient = useQueryClient()
  const capabilitiesQuery = useApplicableCapabilities(context)
  const [search, setSearch] = useState('')
  const [selectedFamily, setSelectedFamily] = useState('all')
  const runnerHeadingRef = useRef<HTMLHeadingElement>(null)
  const returnButtonRef = useRef<HTMLButtonElement | null>(null)
  const [selectedDraft, setSelectedDraft] = useState<string | null>(null)
  const [selectedDraftRevision, setSelectedDraftRevision] = useState<number | null>(null)
  const [selectedDraftContextHash, setSelectedDraftContextHash] = useState<string | null>(null)
  const [activeCapability, setActiveCapability] = useState<AdvancedAnalysisCapability | null>(null)
  const [activeJob, setActiveJob] = useState<AdvancedJobResponse | null>(null)
  const [activeResult, setActiveResult] = useState<AdvancedResultResponse | null>(null)
  const draftMutation = useMutation({
    mutationFn: (capability: ApplicableCapability) => createAnalysisDraft(context.dataset.id, {
      sliceId: capability.sliceId,
      contextHash: context.contextHash,
    }),
    onSuccess: (draft, capability) => {
      setSelectedDraft(draft.id)
      setSelectedDraftRevision(draft.revision)
      setSelectedDraftContextHash(draft.contextHash)
      setActiveCapability(wizardCapability(capability))
      setActiveJob(null)
      setActiveResult(null)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['applicable-capabilities'] }),
  })
  const allCapabilities = capabilitiesQuery.data?.capabilities ?? []
  const visible = useMemo(
    () => allCapabilities.filter(capability => capability.productVisible && capability.executionAvailable && capability.applicable)
      .sort((a, b) => (FAMILY_ORDER.indexOf(a.family) < 0 ? FAMILY_ORDER.length : FAMILY_ORDER.indexOf(a.family)) - (FAMILY_ORDER.indexOf(b.family) < 0 ? FAMILY_ORDER.length : FAMILY_ORDER.indexOf(b.family))),
    [allCapabilities],
  )
  const blocked = useMemo(
    () => allCapabilities.filter(capability => capability.productVisible && capability.executionAvailable && !capability.applicable),
    [allCapabilities],
  )
  const families = useMemo(() => Array.from(new Set(visible.map(capability => capability.family))), [visible])
  const effectiveFamily = families.includes(selectedFamily) ? selectedFamily : 'all'
  const filtered = visible.filter(capability => (effectiveFamily === 'all' || capability.family === effectiveFamily)
    && `${capability.label} ${familyLabel(capability.family)} ${capability.supportBoundary}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()))
  const groups = filtered.reduce<Record<string, ApplicableCapability[]>>((result, capability) => {
    result[capability.family] = [...(result[capability.family] ?? []), capability]
    return result
  }, {})
  const wizardVariables = useMemo(() => toWizardVariables(variables), [variables])
  const draftValidityQuery = useQuery({
    queryKey: ['analysis-draft-validity', selectedDraft, context.contextHash],
    queryFn: () => getAnalysisDraftValidity(selectedDraft ?? ''),
    enabled: Boolean(selectedDraft),
    staleTime: 0,
  })
  const draftContextChanged = Boolean(
    selectedDraftContextHash && selectedDraftContextHash !== context.contextHash,
  )
  const draftIsStale = draftContextChanged || draftValidityQuery.data?.validity === 'stale'
  useEffect(() => {
    if (activeCapability || draftIsStale) runnerHeadingRef.current?.focus()
    else returnButtonRef.current?.focus()
  }, [activeCapability, draftIsStale])
  const resetSelectedDraft = () => {
    setSelectedDraft(null)
    setSelectedDraftRevision(null)
    setSelectedDraftContextHash(null)
    setActiveCapability(null)
    setActiveJob(null)
    setActiveResult(null)
    draftMutation.reset()
  }

  return (
    <main className="context-methods-workspace">
      <header className="methods-page-heading">
        <div><h1>方法目录</h1><p>找到需要的方法，选择变量和参数后单独运行。</p></div>
        <span className="status-chip">{visible.length} 个当前可用方法</span>
      </header>
      <ContextReadinessPanel context={context} onPrepare={onPrepare} />
      {draftIsStale ? (
        <section className="context-method-runner" aria-labelledby="stale-draft-heading">
          <h2 id="stale-draft-heading" tabIndex={-1} ref={runnerHeadingRef}>需要重新确认当前分析草稿</h2>
          <InvalidationNotice
            validity="stale"
            missingRequirements={[]}
            warnings={[]}
            invalidation={draftValidityQuery.data?.invalidation ?? null}
            invalidationReasons={draftValidityQuery.data?.invalidationReasons ?? ['当前上下文哈希已变化']}
          />
          <button type="button" className="run-button" onClick={resetSelectedDraft}>
            返回目录重新配置
          </button>
        </section>
      ) : activeCapability ? (
        <section className="context-method-runner" aria-labelledby="context-method-runner-heading">
          <header>
            <p className="eyebrow">配置当前方法</p>
            <h2 id="context-method-runner-heading" tabIndex={-1} ref={runnerHeadingRef}>{activeCapability.label}</h2>
            <p className="muted">已带入当前数据和已确认的变量角色。检查设置后，再提交运行。</p>
          </header>
          {activeCapability.family === 'multiple_imputation' ? (
            <ImputationPlanWorkspace
              context={context}
              variables={wizardVariables}
              draftId={selectedDraft}
            />
          ) : !activeJob ? (
            <AnalysisWizard
              capability={activeCapability}
              datasetId={context.dataset.id}
              variables={wizardVariables}
              context={context}
              draftId={selectedDraft}
              draftRevision={selectedDraftRevision}
              onJobStarted={setActiveJob}
            />
          ) : activeJob.status === 'succeeded' && activeResult ? (
            <AdvancedResultView
              result={activeResult}
              capability={activeCapability}
              jobId={activeJob.id}
              onNewAnalysis={() => {
                setActiveJob(null)
                setActiveResult(null)
              }}
            />
          ) : (
            <JobProgress
              jobId={activeJob.id}
              initialJob={activeJob}
              capability={activeCapability}
              onComplete={(job, result) => {
                setActiveJob(job)
                setActiveResult(result ?? null)
              }}
              onCancel={() => {
                setActiveJob(null)
                setActiveResult(null)
              }}
            />
          )}
          <button type="button" className="secondary-button" onClick={resetSelectedDraft} disabled={activeJob?.status === 'queued' || activeJob?.status === 'running'}>返回方法目录</button>
        </section>
      ) : null}
      <section className="context-method-catalog" aria-labelledby="context-method-heading" hidden={Boolean(activeCapability) || draftIsStale}>
        <header>
          <h2 id="context-method-heading" className="sr-only">选择分析方法</h2>
        </header>
        <div className="method-catalog-filters">
          <label>搜索方法<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder="输入名称或关键词，如回归、ANOVA、缺失" /></label>
          <label>方法分类<select value={effectiveFamily} onChange={event => setSelectedFamily(event.target.value)}><option value="all">全部分类</option>{families.map(family => <option key={family} value={family}>{familyLabel(family)}</option>)}</select></label>
          <button type="button" className="secondary-button" disabled={!search && effectiveFamily === 'all'} onClick={() => { setSearch(''); setSelectedFamily('all') }}>清除筛选</button>
        </div>
        {!capabilitiesQuery.isLoading && !capabilitiesQuery.error ? <p className="catalog-result-count" role="status">显示 {filtered.length} / {visible.length} 个可用方法</p> : null}
        {capabilitiesQuery.isLoading ? <p aria-live="polite">正在读取适用方法…</p> : null}
        {capabilitiesQuery.error ? <div role="alert"><p className="error-message">方法目录读取失败：{capabilitiesQuery.error.message}</p><button type="button" className="secondary-button" onClick={() => capabilitiesQuery.refetch()}>重新加载目录</button></div> : null}
        {draftMutation.error ? <p className="error-message" role="alert">无法打开方法配置：{draftMutation.error.message}。请检查数据设置后重试。</p> : null}
        {!capabilitiesQuery.isLoading && !capabilitiesQuery.error && visible.length === 0 ? <p className="method-note">当前没有可用方法。请先在“数据准备”中确认变量和研究结构，或查看下方的不可用原因。</p> : null}
        {visible.length > 0 && filtered.length === 0 ? <p className="method-note">没有匹配的方法。试试其他关键词，或清除筛选。</p> : null}
        <div className="context-method-groups">
          {Object.entries(groups).map(([family, entries]) => (
            <section key={family} aria-labelledby={`method-family-${family}`}>
              <h2 id={`method-family-${family}`}>{familyLabel(family)}</h2>
              <div className="context-method-grid">
                {entries.map(capability => (
                  <article key={capability.sliceId} className="context-method-card" aria-label={capability.label}>
                    <div>
                      <h3>{capability.label}</h3>
                      <span className="context-method-status">{maturityLabel(capability.maturityLevel)}</span>
                      <p className="muted">{capability.supportBoundary}</p>
                      <p className="context-method-publication" title={capability.publicationEligibilityReason}>
                        {publicationLabel(capability.publicationEligibility)}
                      </p>
                    </div>
                    {capability.applicable && capability.executionAvailable ? (
                      (() => {
                        const target = internalWorkbenchTarget(capability)
                        if (target) {
                          return (
                            <button
                              type="button"
                              className="run-button"
                              aria-label={`配置${capability.label}`}
                              onClick={() => onNavigate?.(target)}
                              disabled={!onNavigate}
                            >
                              选择变量与参数 →
                            </button>
                          )
                        }
                        return (
                          <button type="button" className="run-button" aria-label={`配置${capability.label}`} onClick={event => { returnButtonRef.current = event.currentTarget; draftMutation.mutate(capability) }} disabled={draftMutation.isPending}>
                            {draftMutation.isPending && draftMutation.variables?.sliceId === capability.sliceId ? '正在打开…' : '选择变量与参数 →'}
                          </button>
                        )
                      })()
                    ) : (
                      <p className="context-blocked-reason">不可用：{capability.blockedReason ?? capability.missingRequirements.join('、')}</p>
                    )}
                  </article>
                ))}
              </div>
            </section>
          ))}
        </div>
        {blocked.length > 0 ? (
          <details className="context-blocked-methods">
            <summary>查看 {blocked.length} 个当前不可用的方法及原因</summary>
            <ul>
              {blocked.map(capability => <li key={capability.sliceId}>{capability.label}：{capability.blockedReason ?? capability.missingRequirements.join('、')}</li>)}
            </ul>
          </details>
        ) : null}
      </section>
    </main>
  )
}
