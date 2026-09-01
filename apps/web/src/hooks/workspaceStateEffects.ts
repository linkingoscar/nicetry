import { useEffect, type Dispatch, type SetStateAction } from 'react'

import { ApiError, getDataset, getMeasurement, getStudyContext } from '../api'
import type {
  DatasetVersion,
  MeasurementVersion,
  StudyContext,
  StudyIntent,
} from '../types'
import { writeActiveDatasetId, writeActiveMeasurementVersion, writeActiveView, writeStudyContext, writeStudyIntent } from './workspaceStateStorage'
import type { WorkspaceView } from './workspaceStateTypes'

export function useWorkspaceCommandPaletteShortcut(
  setIsCommandPaletteOpen: Dispatch<SetStateAction<boolean>>,
): void {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setIsCommandPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [setIsCommandPaletteOpen])
}

export function useWorkspaceStorageSync(
  activeView: WorkspaceView,
  studyIntent: StudyIntent | null,
  studyContext: StudyContext,
): void {
  useEffect(() => {
    writeActiveView(activeView)
  }, [activeView])

  useEffect(() => {
    writeStudyIntent(studyIntent)
  }, [studyIntent])

  useEffect(() => {
    writeStudyContext(studyContext)
  }, [studyContext])
}

export function useInitialStudyContextFetch(
  studyContextTouchedRef: { current: boolean },
  studyContextRevisionRef: { current: number | null },
  setStudyContext: Dispatch<SetStateAction<StudyContext>>,
  setPersistence: (status: 'saved') => void,
): void {
  useEffect(() => {
    let active = true
    getStudyContext('default')
      .then((record) => {
        if (!active || studyContextTouchedRef.current) return
        studyContextRevisionRef.current = record.revision
        setStudyContext({
          schemaVersion: record.schemaVersion,
          timeStructure: record.timeStructure,
          dependenceStructure: record.dependenceStructure,
          design: record.design,
        })
        setPersistence('saved')
      })
      .catch((error) => {
        if (!(error instanceof ApiError && error.status === 404)) {
          console.error('Failed to load project study context:', error)
        }
      })
    return () => {
      active = false
    }
  }, [setStudyContext, setPersistence, studyContextRevisionRef, studyContextTouchedRef])
}

export function useResolvedStudyContextRevisionSync(
  resolvedStudyContext: { revision: number } | null | undefined,
  studyContextRevisionRef: { current: number | null },
): void {
  useEffect(() => {
    if (resolvedStudyContext) {
      const resolvedRevision = resolvedStudyContext.revision
      if (studyContextRevisionRef.current === null || resolvedRevision >= studyContextRevisionRef.current) {
        studyContextRevisionRef.current = resolvedRevision
      }
    }
  }, [resolvedStudyContext, studyContextRevisionRef])
}

export function useWorkspaceNavAutoScroll(
  workspaceNavRef: { current: HTMLDivElement | null },
  activeView: WorkspaceView,
): void {
  useEffect(() => {
    const activeButton = workspaceNavRef.current?.querySelector<HTMLButtonElement>(`button[data-workspace-view="${activeView}"]`)
    if (activeButton && typeof activeButton.scrollIntoView === 'function') {
      activeButton.scrollIntoView({ block: 'nearest', inline: 'nearest' })
    }
  }, [activeView, workspaceNavRef])
}

export function useWorkspaceDatasetSync(
  activeDatasetId: string | null,
  activeMeasurementVersion: number | null,
): void {
  useEffect(() => {
    writeActiveDatasetId(activeDatasetId)
  }, [activeDatasetId])

  useEffect(() => {
    writeActiveMeasurementVersion(activeMeasurementVersion)
  }, [activeMeasurementVersion])
}

interface UseWorkspaceHydrationOptions {
  activeDatasetId: string | null
  activeMeasurementVersion: number | null
  setActiveDataset: Dispatch<SetStateAction<DatasetVersion | null>>
  setModelContext: Dispatch<SetStateAction<{ dataset: DatasetVersion; measurement: MeasurementVersion } | null>>
  setHydrating: Dispatch<SetStateAction<boolean>>
  setActiveDatasetId: Dispatch<SetStateAction<string | null>>
  setActiveMeasurementVersion: Dispatch<SetStateAction<number | null>>
}

export function useWorkspaceHydration({
  activeDatasetId,
  activeMeasurementVersion,
  setActiveDataset,
  setModelContext,
  setHydrating,
  setActiveDatasetId,
  setActiveMeasurementVersion,
}: UseWorkspaceHydrationOptions): void {
  useEffect(() => {
    if (!activeDatasetId) {
      setActiveDataset(null)
      setModelContext(null)
      setHydrating(false)
      return
    }
    let active = true
    const hydrate = async () => {
      setHydrating(true)
      try {
        const dataset = await getDataset(activeDatasetId)
        let measurement: MeasurementVersion | null = null
        if (activeMeasurementVersion !== null) {
          try {
            measurement = await getMeasurement(activeDatasetId, activeMeasurementVersion)
          } catch (error) {
            if (!(error instanceof ApiError && error.status === 404)) throw error
            setActiveMeasurementVersion(null)
          }
        }
        if (active) {
          setActiveDataset(dataset)
          setModelContext(measurement ? { dataset, measurement } : null)
        }
      } catch (err) {
        console.error('Failed to restore workspace from localStorage:', err)
        if (active) {
          setActiveDatasetId(null)
          setActiveMeasurementVersion(null)
          setActiveDataset(null)
          setModelContext(null)
        }
      } finally {
        if (active) {
          setHydrating(false)
        }
      }
    }
    hydrate()
    return () => {
      active = false
    }
  }, [activeDatasetId, activeMeasurementVersion, setActiveDataset, setActiveDatasetId, setActiveMeasurementVersion, setHydrating, setModelContext])
}

export function useWorkspaceViewShortcuts(
  analysisReady: boolean,
  setActiveView: Dispatch<SetStateAction<WorkspaceView>>,
): void {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeEl = document.activeElement
      const isInput = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA' || activeEl.tagName === 'SELECT')
      if (isInput) return

      if ((e.ctrlKey || e.altKey) && !e.shiftKey) {
        if (e.key === '1') {
          e.preventDefault()
          setActiveView('data')
        } else if (e.key === '2' && analysisReady) {
          e.preventDefault()
          setActiveView('empirical')
        } else if (e.key === '3' && analysisReady) {
          e.preventDefault()
          setActiveView('model')
        } else if (e.key === '4' && analysisReady) {
          e.preventDefault()
          setActiveView('methods')
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [analysisReady, setActiveView])
}
