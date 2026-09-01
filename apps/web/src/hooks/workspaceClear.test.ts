import { QueryClient } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { DatasetVersion, MeasurementVersion } from '../types'
import { createWorkspaceStateHandlers, type WorkspaceStateHandlersDeps } from './workspaceStateHandlers'

function setup() {
  const deps: WorkspaceStateHandlersDeps = {
    queryClient: new QueryClient(), workspaceEpochRef: { current: 0 },
    studyContextTouchedRef: { current: false }, studyContextSaveQueueRef: { current: Promise.resolve() }, studyContextRevisionRef: { current: null },
    effectiveStudyContext: { schemaVersion: '1.0.0', timeStructure: 'cross_sectional', dependenceStructure: 'independent', design: 'observational' },
    activeDatasetId: 'dataset_old', activeDataset: null, modelContext: null,
    setStudyContext: vi.fn(), setStudyContextSaveError: vi.fn(), setStudyContextPersistence: vi.fn(), setStudyIntent: vi.fn(),
    setActiveView: vi.fn(), setActiveDataset: vi.fn(), setActiveDatasetId: vi.fn(), setActiveMeasurementVersion: vi.fn(), setModelContext: vi.fn(), setEmpiricalTabRequest: vi.fn(), setLoadingDemo: vi.fn(),
  }
  return { deps, handlers: createWorkspaceStateHandlers(deps) }
}

afterEach(() => vi.restoreAllMocks())

describe('clear current workspace', () => {
  it('keeps state and outstanding callbacks intact if confirmation is cancelled', () => {
    const { deps, handlers } = setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    expect(handlers.handleClearWorkspace()).toBe(false)
    expect(deps.workspaceEpochRef.current).toBe(0)
    expect(deps.setActiveDataset).not.toHaveBeenCalled()
  })
  it('invalidates late dataset and measurement callbacks without cancelling background jobs', () => {
    const { deps, handlers } = setup()
    const cancel = vi.spyOn(deps.queryClient, 'cancelQueries')
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    expect(handlers.handleClearWorkspace()).toBe(true)
    handlers.handleDatasetReady({ id: 'dataset_old' } as DatasetVersion)
    handlers.handleMeasurementReady({ id: 'dataset_old' } as DatasetVersion, { version: 3 } as MeasurementVersion)
    expect(deps.setActiveDataset).toHaveBeenCalledExactlyOnceWith(null)
    expect(deps.setModelContext).toHaveBeenCalledExactlyOnceWith(null)
    expect(deps.setActiveMeasurementVersion).toHaveBeenCalledExactlyOnceWith(null)
    expect(cancel).not.toHaveBeenCalled()
  })
})
