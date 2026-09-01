import type { Dispatch, SetStateAction } from 'react'
import type { QueryClient } from '@tanstack/react-query'

import { ApiError, getStudyContext, loadDemoProject, saveStudyContext } from '../api'
import type { EmpiricalResultTab } from '../components/empirical/EmpiricalResultsNav'
import { showToast } from '../components/shared/Toast'
import type {
  DatasetVersion,
  MeasurementVersion,
  StudyContext,
  StudyIntent,
} from '../types'
import type { WorkspaceView } from './workspaceStateTypes'

export interface WorkspaceStateHandlersDeps {
  workspaceEpochRef: { current: number }
  queryClient: QueryClient
  studyContextTouchedRef: { current: boolean }
  studyContextSaveQueueRef: { current: Promise<void> }
  studyContextRevisionRef: { current: number | null }
  effectiveStudyContext: StudyContext
  activeDatasetId: string | null
  activeDataset: DatasetVersion | null
  modelContext: { dataset: DatasetVersion; measurement: MeasurementVersion } | null
  setStudyContext: Dispatch<SetStateAction<StudyContext>>
  setStudyContextSaveError: Dispatch<SetStateAction<string | null>>
  setStudyContextPersistence: (status: 'unconfirmed' | 'saving' | 'saved' | 'error') => void
  setStudyIntent: Dispatch<SetStateAction<StudyIntent | null>>
  setActiveView: Dispatch<SetStateAction<WorkspaceView>>
  setActiveDataset: Dispatch<SetStateAction<DatasetVersion | null>>
  setActiveDatasetId: Dispatch<SetStateAction<string | null>>
  setActiveMeasurementVersion: Dispatch<SetStateAction<number | null>>
  setModelContext: Dispatch<SetStateAction<{ dataset: DatasetVersion; measurement: MeasurementVersion } | null>>
  setEmpiricalTabRequest: Dispatch<SetStateAction<{ tab: EmpiricalResultTab; key: number } | null>>
  setLoadingDemo: Dispatch<SetStateAction<boolean>>
}

export function createWorkspaceStateHandlers({
  queryClient,
  workspaceEpochRef,
  studyContextTouchedRef,
  studyContextSaveQueueRef,
  studyContextRevisionRef,
  effectiveStudyContext,
  activeDatasetId,
  activeDataset,
  modelContext,
  setStudyContext,
  setStudyContextSaveError,
  setStudyContextPersistence,
  setStudyIntent,
  setActiveView,
  setActiveDataset,
  setActiveDatasetId,
  setActiveMeasurementVersion,
  setModelContext,
  setEmpiricalTabRequest,
  setLoadingDemo,
}: WorkspaceStateHandlersDeps) {
  const epoch = workspaceEpochRef.current
  const handleMeasurementReady = (dataset: DatasetVersion, measurement: MeasurementVersion) => {
    if (epoch !== workspaceEpochRef.current) return
    setActiveDataset(dataset)
    setActiveDatasetId(dataset.id)
    setActiveMeasurementVersion(measurement.version)
    setModelContext({ dataset, measurement })
    setActiveView(
      effectiveStudyContext.timeStructure === 'cross_sectional' && effectiveStudyContext.dependenceStructure === 'nested'
        ? 'methods'
        : 'empirical',
    )
  }

  const handleDatasetReady = (dataset: DatasetVersion) => {
    const datasetChanged = dataset.id !== activeDatasetId
    if (epoch !== workspaceEpochRef.current) return
    setActiveDataset(dataset)
    setActiveDatasetId(dataset.id)
    if (datasetChanged) {
      setActiveMeasurementVersion(null)
      setModelContext(null)
      setEmpiricalTabRequest(null)
      setActiveView('data')
    } else {
      setModelContext((current) => (current && current.dataset.id === dataset.id ? { ...current, dataset } : current))
    }
  }

  const handleStructureSaved = () => {
    if (activeDatasetId) {
      void queryClient.invalidateQueries({ queryKey: ['resolved-analysis-context', activeDatasetId] })
    }
  }

  const handleLoadDemo = async () => {
    setLoadingDemo(true)
    try {
      const payload = await loadDemoProject(effectiveStudyContext.timeStructure)
      if (epoch !== workspaceEpochRef.current) return
      setActiveDataset(payload.dataset)
      setActiveDatasetId(payload.dataset.id)
      setActiveMeasurementVersion(payload.measurement.version)
      setModelContext({ dataset: payload.dataset, measurement: payload.measurement })
      setActiveView('data')
    } catch (error: unknown) {
      showToast(`加载演示项目失败：${error instanceof Error ? error.message : '未知错误'}`, 'error')
    } finally {
      setLoadingDemo(false)
    }
  }

  const handleIntentSelect = (intent: StudyIntent) => {
    setStudyIntent(intent)
    setActiveView(intent === 'analyze' ? 'data' : 'methods')
  }

  const handleStudyContextChange = (next: StudyContext) => {
    const timeStructureChanged = next.timeStructure !== effectiveStudyContext.timeStructure
    const dependenceChanged = next.dependenceStructure !== effectiveStudyContext.dependenceStructure
    const designChanged = next.design !== effectiveStudyContext.design
    studyContextTouchedRef.current = true
    setStudyContext(next)
    setStudyContextSaveError(null)
    setStudyContextPersistence('saving')
    const projectId = activeDataset?.projectId ?? modelContext?.dataset.projectId ?? 'default'
    const pending = studyContextSaveQueueRef.current
      .catch(() => undefined)
      .then(async () => {
        let saved: Awaited<ReturnType<typeof saveStudyContext>>
        try {
          saved = await saveStudyContext(projectId, next, studyContextRevisionRef.current)
        } catch (error) {
          if (!(error instanceof ApiError && error.status === 409)) throw error
          const latest = await getStudyContext(projectId)
          studyContextRevisionRef.current = latest.revision
          saved = await saveStudyContext(projectId, next, latest.revision)
        }
        studyContextRevisionRef.current = saved.revision
        if (activeDatasetId) {
          await queryClient.invalidateQueries({ queryKey: ['resolved-analysis-context', activeDatasetId] })
        }
        if (studyContextSaveQueueRef.current === pending) setStudyContextPersistence('saved')
      })
      .catch((error) => {
        if (studyContextSaveQueueRef.current !== pending) return
        setStudyContextPersistence('error')
        const message = error instanceof Error ? error.message : '未知错误'
        setStudyContextSaveError(`研究上下文未保存：${message}。请重试，当前页面状态仅是本地暂存。`)
      })
    studyContextSaveQueueRef.current = pending
    if (!activeDataset || (!timeStructureChanged && !dependenceChanged && !designChanged)) return
    setActiveView('data')
    setEmpiricalTabRequest({
      tab: next.timeStructure === 'panel'
        ? 'longitudinal'
        : next.timeStructure === 'intensive_longitudinal'
          ? 'diary'
          : 'overview',
      key: Date.now(),
    })
  }

  const handleClearWorkspace = () => {
    const confirmed = window.confirm('清空当前数据并返回导入状态？当前数据、测量和模型将从界面退出；已保存的数据、草稿和结果仍保留在本机。正在后台执行的任务不会被取消。')
    if (!confirmed) return false
    workspaceEpochRef.current += 1
    setActiveDatasetId(null)
    setActiveMeasurementVersion(null)
    setActiveDataset(null)
    setModelContext(null)
    setEmpiricalTabRequest(null)
    setActiveView('data')
    return true
  }

  const handleReturnToStart = () => {
    setStudyIntent(null)
    setActiveView('data')
  }

  return {
    handleMeasurementReady,
    handleDatasetReady,
    handleStructureSaved,
    handleLoadDemo,
    handleIntentSelect,
    handleStudyContextChange,
    handleClearWorkspace,
    handleReturnToStart,
  }
}
