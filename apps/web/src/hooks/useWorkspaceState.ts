import { useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import type { EmpiricalTabRequest } from '../components/context/workbenchNavigation'
import type { AnalysisParadigm, DatasetVersion, MeasurementVersion, StudyContext, StudyIntent } from '../types'
import { useResolvedAnalysisContext } from './useResolvedAnalysisContext'
import {
  useInitialStudyContextFetch,
  useResolvedStudyContextRevisionSync,
  useWorkspaceCommandPaletteShortcut,
  useWorkspaceDatasetSync,
  useWorkspaceHydration,
  useWorkspaceNavAutoScroll,
  useWorkspaceStorageSync,
  useWorkspaceViewShortcuts,
} from './workspaceStateEffects'
import { createWorkspaceStateHandlers } from './workspaceStateHandlers'
import { buildWorkspaceSteps } from './workspaceStateSelectors'
import {
  readActiveDatasetId,
  readActiveMeasurementVersion,
  readActiveView,
  readStudyContext,
  readStudyIntent,
} from './workspaceStateStorage'
import type { WorkspaceView } from './workspaceStateTypes'

export type { WorkspaceView } from './workspaceStateTypes'

export function useWorkspaceState() {
  const workspaceNavRef = useRef<HTMLDivElement>(null)
  const queryClient = useQueryClient()
  const workspaceEpochRef = useRef(0)
  const studyContextTouchedRef = useRef(false)
  const studyContextSaveQueueRef = useRef<Promise<void>>(Promise.resolve())
  const studyContextRevisionRef = useRef<number | null>(null)
  const [studyContextSaveError, setStudyContextSaveError] = useState<string | null>(null)
  const [studyContextPersistence, setStudyContextPersistence] = useState<'unconfirmed' | 'saving' | 'saved' | 'error'>('unconfirmed')

  const [studyIntent, setStudyIntent] = useState<StudyIntent | null>(() => readStudyIntent())
  const [studyContext, setStudyContext] = useState<StudyContext>(() => readStudyContext())
  const [activeView, setActiveView] = useState<WorkspaceView>(() => readActiveView())
  const [loadingDemo, setLoadingDemo] = useState(false)
  const [activeDatasetId, setActiveDatasetId] = useState<string | null>(() => readActiveDatasetId())
  const [activeDataset, setActiveDataset] = useState<DatasetVersion | null>(null)
  const [activeMeasurementVersion, setActiveMeasurementVersion] = useState<number | null>(() => readActiveMeasurementVersion())
  const [modelContext, setModelContext] = useState<{
    dataset: DatasetVersion
    measurement: MeasurementVersion
  } | null>(null)
  const [hydrating, setHydrating] = useState(false)
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false)
  const [empiricalTabRequest, setEmpiricalTabRequest] = useState<EmpiricalTabRequest | null>(null)

  const resolvedContextQuery = useResolvedAnalysisContext(activeDatasetId, activeMeasurementVersion)
  const resolvedContext = resolvedContextQuery.data ?? null
  const resolvedStudyContext = resolvedContext?.studyContext
  const effectiveStudyContext: StudyContext = studyContextTouchedRef.current ? studyContext : resolvedContext?.studyContext?.value ?? studyContext
  const analysisReady = Boolean(activeDataset?.dictionary.status === 'confirmed' && resolvedContext?.validity === 'ready')

  const researchParadigm: AnalysisParadigm = effectiveStudyContext.timeStructure === 'panel'
    ? 'longitudinal'
    : effectiveStudyContext.timeStructure === 'intensive_longitudinal'
      ? 'diary'
      : 'questionnaire'

  useWorkspaceCommandPaletteShortcut(setIsCommandPaletteOpen)
  useWorkspaceStorageSync(activeView, studyIntent, studyContext)
  useInitialStudyContextFetch(studyContextTouchedRef, studyContextRevisionRef, setStudyContext, setStudyContextPersistence)
  useResolvedStudyContextRevisionSync(resolvedStudyContext, studyContextRevisionRef)
  useWorkspaceNavAutoScroll(workspaceNavRef, activeView)
  useWorkspaceDatasetSync(activeDatasetId, activeMeasurementVersion)
  useWorkspaceHydration({
    activeDatasetId,
    activeMeasurementVersion,
    setActiveDataset,
    setModelContext,
    setHydrating,
    setActiveDatasetId,
    setActiveMeasurementVersion,
  })
  useWorkspaceViewShortcuts(analysisReady, setActiveView)

  const {
    handleMeasurementReady,
    handleDatasetReady,
    handleStructureSaved,
    handleLoadDemo,
    handleIntentSelect,
    handleStudyContextChange,
    handleClearWorkspace,
    handleReturnToStart,
  } = createWorkspaceStateHandlers({
    workspaceEpochRef,
    queryClient,
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
  })

  const workspaceSteps = useMemo(
    () => buildWorkspaceSteps({
      activeDataset,
      analysisReady,
    }),
    [activeDataset, analysisReady],
  )

  return {
    workspaceNavRef,
    studyIntent,
    studyContext,
    effectiveStudyContext,
    studyContextSaveError,
    studyContextPersistence,
    activeView,
    setActiveView,
    loadingDemo,
    activeDatasetId,
    activeDataset,
    activeMeasurementVersion,
    modelContext,
    hydrating,
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    empiricalTabRequest,
    setEmpiricalTabRequest,
    resolvedContextQuery,
    resolvedContext,
    analysisReady,
    researchParadigm,
    workspaceSteps,
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
