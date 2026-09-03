import { useEffect, useMemo, useRef, useState, useTransition } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  cancelEmpiricalAnalysisJob,
  getEmpiricalAnalysisJob,
  listAnalysisSamples,
  runEmpiricalAnalysis,
} from '../../api'
import type { EmpiricalConfigValue } from './EmpiricalAnalysisConfig'
import type { EmpiricalTabRequest } from '../context/workbenchNavigation'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'
import {
  deriveEmpiricalState,
  initialEmpiricalConfig,
  optionsFromEmpiricalConfig,
} from './empiricalStateDerived'
import type {
  DatasetVersion,
  EmpiricalAnalysisJob,
  EmpiricalAnalysisOptions,
  MeasurementVersion,
} from '../../types'
import type { AnalysisParadigm } from '../../types/study-context'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { useApplicableCapabilities } from '../../hooks/useApplicableCapabilities'
import { availableProcedures, procedureDefinition, procedureReadiness } from './empiricalProcedures'
import { readEmpiricalHistory, saveEmpiricalHistory } from './empiricalRunHistory'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import { useJobProgress } from '../../hooks/useJobProgress'
import type { EmpiricalAnalysisContextValue } from './EmpiricalAnalysisContext'
import { useEmpiricalSegmentQueries } from './empiricalSegmentQueries'
import {
  empiricalDraftKey,
  migrateEmpiricalDraftToAnalysis,
  readEmpiricalDraft,
  saveEmpiricalDraft,
} from './empiricalDrafts'
import { configForMethod } from './empiricalMethodNavigation'
import { getResolvedAnalysisContext } from '../../api/analysis-context'

interface UseEmpiricalAnalysisStateArgs {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  tabRequest?: EmpiricalTabRequest
  researchParadigm: AnalysisParadigm
  analysisContext?: ResolvedAnalysisContext | null
  analysisId?: string | null
  analysisProcedure?: EmpiricalProcedure
}

export function useEmpiricalAnalysisState({
  dataset,
  measurement,
  tabRequest,
  researchParadigm,
  analysisContext,
  analysisId,
  analysisProcedure,
}: UseEmpiricalAnalysisStateArgs): EmpiricalAnalysisContextValue {
  const queryClient = useQueryClient()
  const historyKey = `researchpath.empirical.runs.v1:${dataset.id}:${(measurement?.version ?? null)}`
  const [runHistory, setRunHistory] = useState(() => readEmpiricalHistory(historyKey))
  const restoreRun = useRef<string | null>(null)
  const derived = useMemo(
    () => deriveEmpiricalState(dataset, measurement, analysisContext),
    [analysisContext, dataset, measurement],
  )
  const {
    scores,
    groupCandidates,
    aggregationCandidates,
    controlCandidates,
    longitudinalCandidates,
    longitudinalItemGroups,
    subjectCandidates,
    boundClusterId,
    nestedContext,
  } = derived
  const crossSectionalWorkflow = researchParadigm === 'questionnaire'
  const draftKey = empiricalDraftKey(dataset, measurement, analysisContext, analysisId)
  const [initialDraft] = useState(() => {
    if (analysisId && analysisProcedure) {
      return migrateEmpiricalDraftToAnalysis(dataset, measurement, analysisContext, analysisId, analysisProcedure)
    }
    return readEmpiricalDraft(draftKey)
  })
  const appliedTabRequest = useRef(initialDraft?.tabRequestKey)
  const [config, setConfig] = useState<EmpiricalConfigValue>(() => {
    if (initialDraft?.config) return initialDraft.config
    const initial = initialEmpiricalConfig(measurement, derived, researchParadigm)
    return analysisProcedure ? { ...initial, procedure: analysisProcedure } : initial
  })
  const needsSampleContext = Boolean(config.sampleVersionId && config.sampleVersionId !== analysisContext?.sample?.id)
  const sampleContextQuery = useQuery({
    queryKey: ['empirical-sample-context', draftKey, config.sampleVersionId],
    queryFn: ({ signal }) => getResolvedAnalysisContext({ datasetId: dataset.id, measurementVersion: measurement?.version, sampleVersionId: config.sampleVersionId }, signal),
    enabled: needsSampleContext,
    retry: false,
  })
  const executionContext = needsSampleContext ? sampleContextQuery.data : analysisContext
  const capabilitiesQuery = useApplicableCapabilities(executionContext)
  const procedures = availableProcedures(capabilitiesQuery.data?.capabilities ?? [], researchParadigm, nestedContext)
  const [activeRunId, setActiveRunId] = useState<string | null>(initialDraft?.activeRunId ?? null)
  const [lastRunConfig, setLastRunConfig] = useState<EmpiricalConfigValue | null>(initialDraft?.lastRunConfig ?? null)
  const [draftSaveFailed, setDraftSaveFailed] = useState(false)
  const [configExpanded, setConfigExpanded] = useState(true)
  const resultsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setDraftSaveFailed(!saveEmpiricalDraft(draftKey, { config, activeRunId, lastRunConfig, tabRequestKey: appliedTabRequest.current }))
  }, [draftKey, config, activeRunId, lastRunConfig])

  useEffect(() => {
    if (!nestedContext || !boundClusterId) return
    setConfig((current) => ({
      ...current,
      aggregationVariableId: current.aggregationVariableId ?? boundClusterId,
      groupVariableId: null,
      outcomeVariableId: null,
      predictorVariableIds: [],
      controlVariableIds: [],
      responseSurfacePredictorIds: [],
    }))
  }, [boundClusterId, nestedContext])

  useEffect(() => {
    if (crossSectionalWorkflow) return
    setConfig((current) => ({
      ...current,
      groupVariableId: null,
      aggregationVariableId: null,
      outcomeVariableId: null,
      predictorVariableIds: [],
      controlVariableIds: [],
      responseSurfacePredictorIds: [],
    }))
  }, [crossSectionalWorkflow])

  const isConfigStale = useMemo(() => {
    if (!lastRunConfig || !activeRunId) return false
    return JSON.stringify(optionsFromEmpiricalConfig(lastRunConfig, analysisContext)) !== JSON.stringify(optionsFromEmpiricalConfig(config, analysisContext))
  }, [lastRunConfig, activeRunId, config, analysisContext])

  const sampleVersionsQuery = useQuery({
    queryKey: ['analysis-samples', dataset.id],
    queryFn: () => listAnalysisSamples(dataset.id),
    staleTime: 30_000,
  })

  const mutation = useMutation({
    mutationFn: (options: EmpiricalAnalysisOptions) =>
      runEmpiricalAnalysis(dataset.id, (measurement?.version ?? null), options),
    onSuccess: (job, options) => {
      if (options.procedure) {
        const next = [{
          id: job.id,
          procedure: options.procedure,
          createdAt: new Date().toISOString(),
          ...(analysisId ? { analysisId } : {}),
        }, ...runHistory].slice(0, 30)
        setRunHistory(next)
        saveEmpiricalHistory(historyKey, next)
      }
      // A workspace switch may unmount this hook before the accepted response arrives.
      // Persist here as well as in the effect so returning can reconnect to that job.
      setDraftSaveFailed(!saveEmpiricalDraft(draftKey, { config, activeRunId: job.id, lastRunConfig: config, tabRequestKey: appliedTabRequest.current }))
      setActiveRunId(job.id)
      queryClient.setQueryData(['empirical-analysis-job', job.id], job)
    },
  })
  const jobQuery = useQuery({
    queryKey: ['empirical-analysis-job', activeRunId],
    queryFn: () => getEmpiricalAnalysisJob(activeRunId ?? ''),
    enabled: !!activeRunId,
    refetchInterval: (query) => {
      const status = (query.state.data as EmpiricalAnalysisJob | undefined)?.status
      return status && ['succeeded', 'failed', 'cancelled'].includes(status) ? false : 1000
    },
  })
  // SSE can populate a terminal status before GET returns the immutable options.
  // Do not restore or render a history entry from this partial notification.
  const analysisJob = jobQuery.data?.options ? jobQuery.data : undefined
  const isContextStale = Boolean(
    analysisJob?.metadata
    && typeof analysisJob.metadata.contextHash === 'string'
    && executionContext?.contextHash
    && analysisJob.metadata.contextHash !== executionContext.contextHash,
  )
  const isRunning =
    mutation.isPending
    || (!!activeRunId && jobQuery.isFetching && !analysisJob)
    || analysisJob?.status === 'queued'
    || analysisJob?.status === 'running'
    || analysisJob?.status === 'cancelling'
  const report = analysisJob?.status === 'succeeded'
    && analysisJob.datasetId === dataset.id && analysisJob.measurementVersion === (measurement?.version ?? null)
    ? analysisJob : null
  const reportId = report?.reportId
  const resultStatus = (key: 'groups' | 'regression' | 'advanced' | 'longitudinal' | 'diary') => {
    const availability = summaryQuery.data?.resultAvailability?.[key]
    if (availability === 'available') return 'available' as const
    if (availability === 'unavailable') return 'warning' as const
    return 'not_requested' as const
  }

  useJobProgress(activeRunId, ['empirical-analysis-job'])

  const cancelMutation = useMutation({
    mutationFn: (runId: string) => cancelEmpiricalAnalysisJob(runId),
    onSuccess: (job) => {
      queryClient.setQueryData(['empirical-analysis-job', job.id], job)
    },
  })

  useEffect(() => {
    if (!analysisJob || restoreRun.current !== analysisJob.id) return
    if (analysisJob.datasetId !== dataset.id || analysisJob.measurementVersion !== (measurement?.version ?? null)) {
      setActiveRunId(null)
      restoreRun.current = null
      return
    }
    const restored = { ...initialEmpiricalConfig(measurement, derived, researchParadigm), ...analysisJob.options } as EmpiricalConfigValue
    setConfig(restored)
    setLastRunConfig(restored)
    if (analysisJob.options.procedure) setActiveTab(procedureDefinition(analysisJob.options.procedure).tab)
    restoreRun.current = null
  }, [analysisJob, dataset.id, measurement, derived, researchParadigm])

  const [activeTab, setActiveTab] = useState<EmpiricalResultTab>(() => procedureDefinition(config.procedure).tab)
  const [isPending, startTransition] = useTransition()
  const [toastText, setToastText] = useState<string | null>(null)

  useEffect(() => {
    if (tabRequest && tabRequest.key !== appliedTabRequest.current) {
      if (activeRunId && !analysisJob && jobQuery.isFetching) return
      appliedTabRequest.current = tabRequest.key
      setDraftSaveFailed(!saveEmpiricalDraft(draftKey, { config, activeRunId, lastRunConfig, tabRequestKey: tabRequest.key }))
      const target = { overview: 'descriptives', correlation: 'correlation', measurement: 'reliability', groups: nestedContext ? 'aggregation' : 'groups', regression: 'regression', advanced: 'response_surface', longitudinal: 'longitudinal', diary: 'diary' } as const
      if (tabRequest.method && tabRequest.method.contextHash !== analysisContext?.contextHash) return
      if (isRunning) {
        setToastText('当前任务仍在运行，已保留配置；请在任务结束或取消后重新选择目录方法。')
        return
      }
      const requestedProcedure = tabRequest.method?.procedure ?? target[tabRequest.tab]
      const targetProcedure = analysisProcedure ?? requestedProcedure
      const restored = readEmpiricalDraft(draftKey, targetProcedure)
        ?? (analysisId ? migrateEmpiricalDraftToAnalysis(dataset, measurement, analysisContext, analysisId, targetProcedure) : null)
      const base = restored?.config ?? { ...initialEmpiricalConfig(measurement, derived, researchParadigm), procedure: targetProcedure }
      const directBase = tabRequest.method?.procedure && !analysisProcedure ? { ...base, procedure: tabRequest.method.procedure } : base
      const next = tabRequest.method ? configForMethod(directBase, tabRequest.method.sliceId, analysisContext) : directBase
      if (tabRequest.method && JSON.stringify(next) !== JSON.stringify(base)
        && !window.confirm(`进入“${tabRequest.method.label}”将调整本方法草稿的模型类型或所需选项，保留兼容的变量配置；既有结果仍属于原运行配置，不会自动重新计算。取消则保留原草稿。是否继续？`)) {
        setToastText('已取消目录方法切换，原草稿保持不变。')
        return
      }
      setConfig(next)
      if (tabRequest.method) setToastText(`已进入：${tabRequest.method.label}。请检查变量与估计设置后手动运行。`)

      setActiveTab(procedureDefinition(targetProcedure).tab)
      setActiveRunId(restored?.activeRunId ?? null)
      setLastRunConfig(restored?.lastRunConfig ?? null)
      setConfigExpanded(true)
    }
  }, [tabRequest, nestedContext, draftKey, measurement, derived, researchParadigm, analysisContext, analysisId, analysisProcedure, dataset, isRunning, activeRunId, analysisJob, jobQuery.isFetching, config, lastRunConfig])

  const showToast = (msg: string) => {
    setToastText(msg)
    setTimeout(() => setToastText(null), 3000)
  }

  const {
    summaryQuery,
    correlationQuery,
    efaCfaQuery,
    validityQuery,
    regressionQuery,
  } = useEmpiricalSegmentQueries(dataset, measurement, reportId, activeTab)

  const run = () => {
    if (isRunning || (needsSampleContext && (!executionContext || sampleContextQuery.isError || sampleContextQuery.isFetching)) || procedureReadiness(config) || !procedures.some((p) => p.id === config.procedure)) return
    setActiveTab(procedureDefinition(config.procedure).tab)
    setActiveRunId(null)
    setLastRunConfig(config)
    mutation.mutate(optionsFromEmpiricalConfig(config, executionContext))
  }

  useEffect(() => {
    if (!reportId) return
    setConfigExpanded(false)
    window.requestAnimationFrame(() => {
      resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }, [reportId])

  const changeTab = (tab: EmpiricalResultTab) => {
    startTransition(() => setActiveTab(tab))
  }
  const onConfigChange = (patch: Partial<EmpiricalConfigValue>) => {
    setConfig((current) => ({ ...current, ...patch }))
  }

  const analysisRunHistory = runHistory.filter((entry) =>
    (!analysisProcedure || entry.procedure === analysisProcedure)
    && (!analysisId || !entry.analysisId || entry.analysisId === analysisId))

  const onSelectProcedure = (procedure: EmpiricalProcedure) => {
    if (isRunning || (analysisProcedure && procedure !== analysisProcedure)) return
    const restored = readEmpiricalDraft(draftKey, procedure)
      ?? (analysisId ? migrateEmpiricalDraftToAnalysis(dataset, measurement, analysisContext, analysisId, procedure) : null)
    setConfig(restored?.config ?? { ...initialEmpiricalConfig(measurement, derived, researchParadigm), procedure })
    setActiveRunId(restored?.activeRunId ?? null)
    setLastRunConfig(restored?.lastRunConfig ?? null)
    setConfigExpanded(true)
    setActiveTab(procedureDefinition(procedure).tab)
    mutation.reset()
  }
  const onSelectRun = (id: string) => {
    const entry = analysisRunHistory.find((run) => run.id === id)
    if (!entry || isRunning) return
    restoreRun.current = id
    setActiveRunId(id)
    setActiveTab(procedureDefinition(entry.procedure).tab)
    mutation.reset()
  }
  return {
    procedures,
    capabilitiesLoading: capabilitiesQuery.isLoading || (needsSampleContext && sampleContextQuery.isLoading),
    capabilitiesError: capabilitiesQuery.isError || (needsSampleContext && sampleContextQuery.isError),
    allCandidates: [...scores, ...dataset.variables],
    analysisCandidates: [...scores, ...dataset.variables.filter((v) => ['continuous', 'ordinal', 'likert', 'binary'].includes(v.confirmedType ?? v.inferredType))],
    onSelectProcedure,
    runHistory: analysisRunHistory,
    onSelectRun,
    activeRunId,
    measurement,
    scores,
    groupCandidates,
    aggregationCandidates,
    controlCandidates,
    longitudinalCandidates,
    longitudinalItemGroups,
    subjectCandidates,
    contextRoles: analysisContext?.structure?.roles,
    nestedContext,
    sampleVersions: sampleVersionsQuery.data,
    config,
    researchParadigm,
    configExpanded,
    hasReport: !!report,
    isRunning,
    analysisJob,
    cancelPending: cancelMutation.isPending,
    error:
      mutation.error?.message
      ?? sampleContextQuery.error?.message
      ?? (draftSaveFailed ? '浏览器未能保存分析草稿；请勿刷新或离开页面。已提交任务仍保存在服务端。' : null)
      ?? jobQuery.error?.message
      ?? ((analysisJob?.status === 'failed' || analysisJob?.status === 'cancelled')
        ? analysisJob.error ?? (analysisJob.status === 'cancelled' ? '分析已取消' : '分析失败')
        : null),
    onConfigChange,
    onToggleExpanded: () => setConfigExpanded((current) => !current),
    onRun: run,
    onCancel: (runId) => cancelMutation.mutate(runId),
    report,
    isConfigStale,
    isContextStale,
    datasetId: dataset.id,
    datasetName: dataset.originalFile?.name ?? '',
    measurementVersion: (measurement?.version ?? null),
    summaryQuery,
    correlationQuery,
    efaCfaQuery,
    validityQuery,
    regressionQuery,
    activeTab,
    isPending,
    setActiveTab: changeTab,
    resultStatus,
    showToast,
    toastText,
    resultsRef,
  }
}
