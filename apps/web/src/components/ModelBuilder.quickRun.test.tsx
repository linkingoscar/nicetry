import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion, MeasurementVersion, ModelSpec } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import type { MethodRequest } from './context/workbenchNavigation'
import { ModelBuilder } from './ModelBuilder'

const mocks = vi.hoisted(() => ({
  applyProcessQuickSetup: vi.fn(() => true),
  switchEstimationFamily: vi.fn(),
}))

vi.mock('./model-builder/useModelBuilderState', () => ({
  useModelBuilderState: () => ({
    variables: [],
    indicatorCandidates: [],
    template: 'model_4',
    customMode: false,
    model: { estimation: { family: 'ols' }, latents: [], nodes: [] } as ModelSpec,
    validation: null,
    draftState: 'saved',
    builderError: null,
    overrideReason: '',
    setOverrideReason: vi.fn(),
    zenMode: false,
    leftCollapsed: false,
    rightCollapsed: false,
    analysisJob: null,
    analysisResult: undefined,
    analysisRunning: false,
    editingLocked: false,
    freezeMutation: { isPending: false, reset: vi.fn(), mutate: vi.fn() },
    analysisMutation: { isPending: false, reset: vi.fn(), mutate: vi.fn() },
    cancelMutation: { isPending: false, reset: vi.fn(), mutate: vi.fn() },
    canUndo: false,
    canRedo: false,
    updateModel: vi.fn(),
    handleUndo: vi.fn(),
    handleRedo: vi.fn(),
    applyProcessQuickSetup: mocks.applyProcessQuickSetup,
    applyTemplate: vi.fn(),
    startCustomModel: vi.fn(),
    assignVariable: vi.fn(),
    addStructuralNode: vi.fn(),
    removeStructuralNode: vi.fn(),
    addCovariate: vi.fn(),
    addVariableToCanvas: vi.fn(),
    addEdge: vi.fn(),
    removeCanvasNode: vi.fn(),
    changeNodeRole: vi.fn(),
    handleConnect: vi.fn(),
    reconnectEdge: vi.fn(),
    handleResetLayout: vi.fn(),
    setZenMode: vi.fn(),
    setLeftCollapsed: vi.fn(),
    setRightCollapsed: vi.fn(),
    pathEvidence: {},
    recognitionLabel: 'PROCESS',
    contextGateBlocked: false,
    contextBindingStale: false,
    unusedVariables: [],
    switchEstimationFamily: mocks.switchEstimationFamily,
  }),
}))

vi.mock('./model-builder/ProcessQuickSetupForm', () => ({
  ProcessQuickSetupForm: ({ initialKind, onApply, onOpenAdvanced }: {
    initialKind: string
    onApply: (setup: never) => boolean
    onOpenAdvanced: () => void
  }) => (
    <div>
      <span>quick-kind:{initialKind}</span>
      <button type="button" onClick={() => onApply({} as never)}>apply-quick</button>
      <button type="button" onClick={onOpenAdvanced}>open-advanced</button>
    </div>
  ),
}))
vi.mock('./model-builder/ModelBuilderSidebar', () => ({ ModelBuilderSidebar: () => <div>run-controls</div> }))
vi.mock('./model-builder/ModelBuilderToolbar', () => ({ ModelBuilderToolbar: () => <div>advanced-toolbar</div> }))
vi.mock('./model-builder/ModelVariableLibrary', () => ({ ModelVariableLibrary: () => null }))
vi.mock('./model-builder/ModelContextBindingBanner', () => ({ ModelContextBindingBanner: () => null }))
vi.mock('./model-builder/ModelEstimationEditor', () => ({ ModelEstimationEditor: () => null }))
vi.mock('./model-builder/RoleEditorSection', () => ({ RoleEditorSection: () => null }))
vi.mock('./model-builder/PathEditorSection', () => ({ PathEditorSection: () => null }))
vi.mock('./model-builder/ModerationEditor', () => ({ ModerationEditor: () => null }))
vi.mock('./model-builder/CovariateEditor', () => ({ CovariateEditor: () => null }))
vi.mock('./model-builder/SemStudioMeasurementEditor', () => ({ SemStudioMeasurementEditor: () => null }))
vi.mock('./ModelCanvas', () => ({ ModelCanvas: () => null }))
vi.mock('./ResultPanel', () => ({ ResultPanel: () => null }))

const dataset = { id: 'dataset_demo', variables: [] } as unknown as DatasetVersion
const measurement = { id: 'measurement_demo' } as unknown as MeasurementVersion
const context = { contextHash: 'context_demo' } as unknown as ResolvedAnalysisContext

function request(processModelNumber?: 1 | 4): MethodRequest {
  return {
    sliceId: 'model.process_catalog',
    label: processModelNumber === 1 ? '简单调节' : processModelNumber === 4 ? '简单中介' : '完整模型库',
    contextHash: 'context_demo',
    key: 1,
    processModelNumber,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  mocks.applyProcessQuickSetup.mockReturnValue(true)
})

describe('ModelBuilder form-first PROCESS routing', () => {
  it('keeps Model 4 on the quick form and reveals the shared run controls only after apply', async () => {
    render(<ModelBuilder dataset={dataset} measurement={measurement} analysisContext={context} methodRequest={request(4)} />)

    expect(await screen.findByText('quick-kind:mediation')).toBeInTheDocument()
    expect(screen.queryByText('run-controls')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'apply-quick' }))
    expect(mocks.applyProcessQuickSetup).toHaveBeenCalledTimes(1)
    expect(screen.getByText('run-controls')).toBeInTheDocument()
    expect(screen.queryByText('advanced-toolbar')).not.toBeInTheDocument()
  })

  it('opens Model 1 as moderation and keeps the full catalog in the advanced editor', async () => {
    const view = render(<ModelBuilder dataset={dataset} measurement={measurement} analysisContext={context} methodRequest={request(1)} />)
    expect(await screen.findByText('quick-kind:moderation')).toBeInTheDocument()

    view.rerender(<ModelBuilder dataset={dataset} measurement={measurement} analysisContext={context} methodRequest={request()} />)
    expect(await screen.findByText('advanced-toolbar')).toBeInTheDocument()
    expect(screen.queryByText(/quick-kind:/)).not.toBeInTheDocument()
  })
})
