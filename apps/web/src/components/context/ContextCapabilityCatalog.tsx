import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { createAnalysisDraft, getAnalysisDraftValidity } from '../../api/analysis-context'
import { useApplicableCapabilities } from '../../hooks/useApplicableCapabilities'
import { METHOD_CATEGORY_ORDER, methodCategoryLabel } from '../../methods/methodCategories'
import { methodSearchText } from '../../methods/methodDefinitions'
import { libraryMethodsForCapability, type MethodLibraryDefinition } from '../../methods/methodLibraryPresets'
import { resolveMethodAvailability, type MethodAvailability } from '../../methods/resolveMethodAvailability'
import type { ApplicableCapability, ResolvedAnalysisContext } from '../../types/analysis-context'
import type { DatasetVariable } from '../../types/datasets'
import type { AdvancedAnalysisCapability, AdvancedJobResponse, AdvancedResultResponse } from '../../types/advanced'
import { AnalysisWizard } from '../advanced/AnalysisWizard'
import { AdvancedResultView } from '../advanced/AdvancedResultView'
import { JobProgress } from '../advanced/JobProgress'
import { registerOutputRun } from '../analyses/outputRunRegistry'
import { ContextReadinessPanel } from './ContextReadinessPanel'
import { ImputationPlanWorkspace } from './ImputationPlanWorkspace'
import { InvalidationNotice } from './InvalidationNotice'
import {
  internalWorkbenchTarget,
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

interface CatalogEntry {
  capability: ApplicableCapability
  method: MethodLibraryDefinition
  availability: MethodAvailability
}

type DraftSelection = Pick<CatalogEntry, 'capability' | 'method'>
type AvailabilityFilter = 'all' | 'ready' | 'needs-setup' | 'not-applicable'
type TierFilter = 'all' | 'common' | 'advanced'

function categoryRank(categoryId: string): number {
  const index = METHOD_CATEGORY_ORDER.indexOf(categoryId as (typeof METHOD_CATEGORY_ORDER)[number])
  return index < 0 ? METHOD_CATEGORY_ORDER.length : index
}

export function ContextCapabilityCatalog({ context, variables = [], onNavigate, onPrepare }: ContextCapabilityCatalogProps) {
  const queryClient = useQueryClient()
  const capabilitiesQuery = useApplicableCapabilities(context)
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [availabilityFilter, setAvailabilityFilter] = useState<AvailabilityFilter>('all')
  const [tierFilter, setTierFilter] = useState<TierFilter>('all')
  const runnerHeadingRef = useRef<HTMLHeadingElement>(null)
  const returnButtonRef = useRef<HTMLButtonElement | null>(null)
  const [selectedDraft, setSelectedDraft] = useState<string | null>(null)
  const [selectedDraftRevision, setSelectedDraftRevision] = useState<number | null>(null)
  const [selectedDraftContextHash, setSelectedDraftContextHash] = useState<string | null>(null)
  const [activeCapability, setActiveCapability] = useState<AdvancedAnalysisCapability | null>(null)
  const [activeMethodId, setActiveMethodId] = useState<string | null>(null)
  const [activeJob, setActiveJob] = useState<AdvancedJobResponse | null>(null)
  const [activeResult, setActiveResult] = useState<AdvancedResultResponse | null>(null)

  const draftMutation = useMutation({
    mutationFn: ({ capability }: DraftSelection) => createAnalysisDraft(context.dataset.id, {
      sliceId: capability.sliceId,
      contextHash: context.contextHash,
    }),
    onSuccess: (draft, { capability, method }) => {
      setSelectedDraft(draft.id)
      setSelectedDraftRevision(draft.revision)
      setSelectedDraftContextHash(draft.contextHash)
      setActiveCapability({ ...wizardCapability(capability), label: method.label })
      setActiveMethodId(method.libraryId)
      setActiveJob(null)
      setActiveResult(null)
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['applicable-capabilities'] }),
  })

  const allCapabilities = capabilitiesQuery.data?.capabilities ?? []
  const catalogEntries = useMemo<CatalogEntry[]>(() => allCapabilities
    .filter((capability) => capability.productVisible)
    .flatMap((capability) => libraryMethodsForCapability(capability).map((method) => ({
      capability,
      method,
      availability: resolveMethodAvailability(capability),
    })))
    .sort((a, b) => categoryRank(a.method.categoryId) - categoryRank(b.method.categoryId)
      || a.method.label.localeCompare(b.method.label, 'zh-CN')),
  [allCapabilities])

  const categories = useMemo(
    () => Array.from(new Set(catalogEntries.map((entry) => entry.method.categoryId)))
      .sort((a, b) => categoryRank(a) - categoryRank(b)),
    [catalogEntries],
  )
  const effectiveCategory = categories.includes(selectedCategory) ? selectedCategory : 'all'
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const filteredEntries = catalogEntries.filter(({ capability, method, availability }) => {
    if (effectiveCategory !== 'all' && method.categoryId !== effectiveCategory) return false
    if (availabilityFilter !== 'all' && availability.state !== availabilityFilter) return false
    if (tierFilter === 'common' && method.visibilityTier !== 'common') return false
    if (tierFilter === 'advanced' && !method.advanced) return false
    if (!normalizedSearch) return true
    return `${methodSearchText(method)} ${capability.supportBoundary}`.toLocaleLowerCase().includes(normalizedSearch)
  })
  const groups = filteredEntries.reduce<Record<string, CatalogEntry[]>>((result, entry) => {
    result[entry.method.categoryId] = [...(result[entry.method.categoryId] ?? []), entry]
    return result
  }, {})

  const readyCount = catalogEntries.filter((entry) => entry.availability.state === 'ready').length
  const needsSetupCount = catalogEntries.filter((entry) => entry.availability.state === 'needs-setup').length
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
    setActiveMethodId(null)
    setActiveJob(null)
    setActiveResult(null)
    draftMutation.reset()
  }

  const clearFilters = () => {
    setSearch('')
    setSelectedCategory('all')
    setAvailabilityFilter('all')
    setTierFilter('all')
  }

  return (
    <main className="context-methods-workspace">
      <header className="methods-page-heading">
        <div>
          <h1>分析方法</h1>
          <p>搜索你要做的分析。方法是否可运行由当前数据和方法自身要求决定。</p>
        </div>
        <span className="status-chip">{readyCount} 个可直接配置 · {needsSetupCount} 个需设置</span>
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
            返回方法库重新配置
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
              onJobStarted={(job) => {
                registerOutputRun({
                  runId: job.id,
                  projectId: context.projectId,
                  datasetVersionId: context.dataset.id,
                  measurementVersionId: context.measurement?.id ?? null,
                  source: 'advanced',
                  label: activeCapability.label,
                  methodId: activeMethodId ?? activeCapability.sliceId ?? activeCapability.family,
                  family: activeCapability.family,
                  createdAt: job.createdAt ?? new Date().toISOString(),
                })
                setActiveJob(job)
              }}
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
          <button type="button" className="secondary-button" onClick={resetSelectedDraft} disabled={activeJob?.status === 'queued' || activeJob?.status === 'running'}>返回方法库</button>
        </section>
      ) : null}

      <section className="context-method-catalog" aria-labelledby="context-method-heading" hidden={Boolean(activeCapability) || draftIsStale}>
        <header>
          <h2 id="context-method-heading" className="sr-only">选择分析方法</h2>
        </header>
        <div className="method-catalog-filters">
          <label>
            搜索方法
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="相关、回归、中介、CFA、RI-CLPM…"
            />
          </label>
          <label>
            研究任务
            <select value={effectiveCategory} onChange={(event) => setSelectedCategory(event.target.value)}>
              <option value="all">全部分类</option>
              {categories.map((categoryId) => <option key={categoryId} value={categoryId}>{methodCategoryLabel(categoryId)}</option>)}
            </select>
          </label>
          <label>
            当前状态
            <select value={availabilityFilter} onChange={(event) => setAvailabilityFilter(event.target.value as AvailabilityFilter)}>
              <option value="all">全部状态</option>
              <option value="ready">可直接配置</option>
              <option value="needs-setup">需要设置</option>
              <option value="not-applicable">当前数据不适用</option>
            </select>
          </label>
          <label>
            方法层级
            <select value={tierFilter} onChange={(event) => setTierFilter(event.target.value as TierFilter)}>
              <option value="all">全部方法</option>
              <option value="common">常用方法</option>
              <option value="advanced">高级方法</option>
            </select>
          </label>
          <button
            type="button"
            className="secondary-button"
            disabled={!search && effectiveCategory === 'all' && availabilityFilter === 'all' && tierFilter === 'all'}
            onClick={clearFilters}
          >
            清除筛选
          </button>
        </div>

        {!capabilitiesQuery.isLoading && !capabilitiesQuery.error ? (
          <p className="catalog-result-count" role="status">显示 {filteredEntries.length} / {catalogEntries.length} 个方法</p>
        ) : null}
        {capabilitiesQuery.isLoading ? <p aria-live="polite">正在读取方法库…</p> : null}
        {capabilitiesQuery.error ? (
          <div role="alert">
            <p className="error-message">方法库读取失败：{capabilitiesQuery.error.message}</p>
            <button type="button" className="secondary-button" onClick={() => capabilitiesQuery.refetch()}>重新加载方法库</button>
          </div>
        ) : null}
        {draftMutation.error ? <p className="error-message" role="alert">无法打开方法配置：{draftMutation.error.message}。请检查数据设置后重试。</p> : null}
        {!capabilitiesQuery.isLoading && !capabilitiesQuery.error && catalogEntries.length === 0 ? <p className="method-note">当前方法注册表没有可展示的方法。</p> : null}
        {catalogEntries.length > 0 && filteredEntries.length === 0 ? <p className="method-note">没有匹配的方法。试试其他关键词或清除筛选。</p> : null}

        <div className="context-method-groups">
          {Object.entries(groups).map(([categoryId, entries]) => (
            <section key={categoryId} aria-labelledby={`method-category-${categoryId}`}>
              <h2 id={`method-category-${categoryId}`}>{methodCategoryLabel(categoryId)}</h2>
              <div className="context-method-grid">
                {entries.map(({ capability, method, availability }) => {
                  const target = availability.state === 'ready' ? internalWorkbenchTarget(capability, method) : null
                  return (
                    <article key={method.libraryId} className="context-method-card" aria-label={method.label}>
                      <div>
                        <h3>{method.label}</h3>
                        <div className="method-card-status-row">
                          <span className={`context-method-status method-status-${availability.state}`}>{availability.label}</span>
                          {capability.maturityLevel === 'experimental' || method.experimental ? (
                            <span className="context-method-status">实验性</span>
                          ) : null}
                        </div>
                        <p>{method.description}</p>
                        <p className="muted">{capability.supportBoundary}</p>
                        {availability.reason ? <p className="context-blocked-reason">{availability.reason}</p> : null}
                      </div>

                      {availability.state === 'ready' ? (
                        target ? (
                          <button
                            type="button"
                            className="run-button"
                            aria-label={`配置${method.label}`}
                            onClick={() => onNavigate?.(target)}
                            disabled={!onNavigate}
                          >
                            选择变量与参数 →
                          </button>
                        ) : (
                          <button
                            type="button"
                            className="run-button"
                            aria-label={`配置${method.label}`}
                            onClick={(event) => {
                              returnButtonRef.current = event.currentTarget
                              draftMutation.mutate({ capability, method })
                            }}
                            disabled={draftMutation.isPending}
                          >
                            {draftMutation.isPending && draftMutation.variables?.capability.sliceId === capability.sliceId ? '正在打开…' : '选择变量与参数 →'}
                          </button>
                        )
                      ) : availability.state === 'needs-setup' ? (
                        <button type="button" className="secondary-button" onClick={onPrepare} disabled={!onPrepare}>
                          完成设置
                        </button>
                      ) : onPrepare ? (
                        <button type="button" className="secondary-button" onClick={onPrepare}>
                          查看数据设置
                        </button>
                      ) : null}
                    </article>
                  )
                })}
              </div>
            </section>
          ))}
        </div>
      </section>
    </main>
  )
}
