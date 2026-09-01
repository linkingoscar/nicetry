import { useEffect } from 'react'
import { useMutation, useQuery, type UseMutationResult } from '@tanstack/react-query'

import {
  cancelAnalysisJob,
  freezeModel,
  getAnalysisJob,
  getAnalysisResult,
  runFrozenModel,
} from '../../api'
import type {
  AnalysisJob,
  DatasetVersion,
  FrozenModelVersion,
  ModelSpec,
  ResultBundle,
} from '../../types'
import { useJobProgress } from '../../hooks/useJobProgress'
import { activeRunStorageKey } from './runPersistence'

interface UseModelBuilderAnalysisOptions {
  dataset: DatasetVersion
  model: ModelSpec
  overrideReason: string
  activeRunId: string | null
  setActiveRunId: (next: string | null) => void
}

export function useModelBuilderAnalysis({
  dataset,
  model,
  overrideReason,
  activeRunId,
  setActiveRunId,
}: UseModelBuilderAnalysisOptions): {
    freezeMutation: UseMutationResult<FrozenModelVersion, Error, void, unknown>
    analysisMutation: UseMutationResult<AnalysisJob, Error, number | undefined, unknown>
    cancelMutation: UseMutationResult<AnalysisJob, Error, void, unknown>
    analysisJob: AnalysisJob | null | undefined
    analysisResult: ResultBundle | undefined
    analysisRunning: boolean
  } {
  const freezeMutation = useMutation({
    mutationFn: () => freezeModel(dataset.id, model, overrideReason),
  })
  const analysisMutation = useMutation({
    mutationFn: (restoredModelVersion?: number) => {
      const modelVersion = freezeMutation.data?.version ?? restoredModelVersion
      if (!modelVersion) throw new Error('请先冻结 ModelVersion')
      return runFrozenModel(dataset.id, model.modelId, modelVersion)
    },
    onSuccess: (job) => setActiveRunId(job.id),
  })
  const analysisQuery = useQuery({
    queryKey: ['analysis-job', activeRunId],
    queryFn: () => {
      if (!activeRunId) throw new Error('分析任务 ID 尚未建立')
      return getAnalysisJob(activeRunId)
    },
    enabled: activeRunId !== null,
    staleTime: Infinity,
  })

  useJobProgress(activeRunId, ['analysis-job'])

  const analysisResultQuery = useQuery({
    queryKey: ['analysis-result', activeRunId],
    queryFn: () => {
      if (!activeRunId) throw new Error('分析任务 ID 尚未建立')
      return getAnalysisResult(activeRunId)
    },
    enabled: activeRunId !== null && analysisQuery.data?.status === 'succeeded',
    staleTime: Infinity,
  })

  useEffect(() => {
    const key = activeRunStorageKey(dataset.id, model.modelId)
    if (activeRunId) localStorage.setItem(key, activeRunId)
    else localStorage.removeItem(key)
  }, [activeRunId, dataset.id, model.modelId])
  const cancelMutation = useMutation({
    mutationFn: () => {
      if (!activeRunId) throw new Error('当前没有运行中的分析')
      return cancelAnalysisJob(activeRunId)
    },
  })

  const analysisJob = analysisQuery.data ?? analysisMutation.data
  const analysisResult = analysisResultQuery.data ?? undefined
  const analysisRunning = analysisMutation.isPending
    || (activeRunId !== null && analysisQuery.isPending)
    || Boolean(analysisJob && ['queued', 'running', 'cancelling'].includes(analysisJob.status))

  return {
    freezeMutation,
    analysisMutation,
    cancelMutation,
    analysisJob,
    analysisResult,
    analysisRunning,
  }
}
