import { useEffect, useState } from 'react'
import type { MethodRequest } from './context/workbenchNavigation'
import type { DatasetVersion, MeasurementVersion } from '../types'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { useModelBuilderState } from './model-builder/useModelBuilderState'
import { ModelBuilderToolbar } from './model-builder/ModelBuilderToolbar'
import { ModelVariableLibrary } from './model-builder/ModelVariableLibrary'
import { ModelContextBindingBanner } from './model-builder/ModelContextBindingBanner'
import { ModelEstimationEditor } from './model-builder/ModelEstimationEditor'
import { ModelBuilderSidebar } from './model-builder/ModelBuilderSidebar'
import { ProcessQuickSetupForm } from './model-builder/ProcessQuickSetupForm'
import type { ProcessQuickKind } from './model-builder/processQuickForm'
import { RoleEditorSection } from './model-builder/RoleEditorSection'
import { PathEditorSection } from './model-builder/PathEditorSection'
import { ModerationEditor } from './model-builder/ModerationEditor'
import { CovariateEditor } from './model-builder/CovariateEditor'
import { ModelCanvas } from './ModelCanvas'
import { ResultPanel } from './ResultPanel'
import { removeModelEdges } from './model-builder/modelStructureActions'
import { SemStudioMeasurementEditor } from './model-builder/SemStudioMeasurementEditor'
import type { SemView } from './model-builder/semCanvasGraph'

interface ModelBuilderProps {
  methodRequest?: MethodRequest | null
  onMethodHandled?: () => void
  dataset: DatasetVersion
  measurement: MeasurementVersion
  analysisContext?: ResolvedAnalysisContext | null
}

export function ModelBuilder({ dataset, measurement, analysisContext, methodRequest, onMethodHandled }: ModelBuilderProps) {
  const {
    variables,
    indicatorCandidates,
    template,
    customMode,
    model,
    validation,
    draftState,
    builderError,
    overrideReason,
    setOverrideReason,
    zenMode,
    leftCollapsed,
    rightCollapsed,
    analysisJob,
    analysisResult,
    analysisRunning,
    editingLocked,
    freezeMutation,
    analysisMutation,
    cancelMutation,
    canUndo,
    canRedo,
    updateModel,
    handleUndo,
    handleRedo,
    applyProcessQuickSetup,
    applyTemplate,
    startCustomModel,
    assignVariable,
    addStructuralNode,
    removeStructuralNode,
    addCovariate,
    addVariableToCanvas,
    addEdge,
    removeCanvasNode,
    changeNodeRole,
    handleConnect,
    reconnectEdge,
    handleResetLayout,
    setZenMode,
    setLeftCollapsed,
    setRightCollapsed,
    pathEvidence,
    recognitionLabel,
    contextGateBlocked,
    contextBindingStale,
    unusedVariables,
    switchEstimationFamily,
  } = useModelBuilderState({ dataset, measurement, analysisContext })

  const [methodNotice, setMethodNotice] = useState<string | null>(null)
  const [processQuickOpen, setProcessQuickOpen] = useState(false)
  const [processQuickKind, setProcessQuickKind] = useState<ProcessQuickKind>('mediation')
  useEffect(() => {
    if (!methodRequest || draftState === 'saving') return
    onMethodHandled?.()
    if (methodRequest.contextHash !== analysisContext?.contextHash) return
    if (editingLocked || draftState === 'error') {
      setMethodNotice('当前任务或草稿尚未就绪，已保留原模型；请就绪后重新选择目录方法。')
      return
    }
    const processRequest = methodRequest.sliceId === 'model.process_catalog'
    const family = methodRequest.sliceId === 'model.sem' ? 'sem' : 'ols'
    if (model.estimation.family !== family) {
      if (!window.confirm(`进入“${methodRequest.label}”需切换估计引擎，将转换节点并重建测量定义、估计器与多组设置；自定义题项、高阶因子及部分等值约束会重置。可撤销恢复，不会自动运行。是否继续？`)) {
        setProcessQuickOpen(false)
        setMethodNotice('已取消目录方法切换，原模型草稿保持不变。')
        return
      }
      switchEstimationFamily(family)
    }
    if (processRequest && methodRequest.processModelNumber) {
      const kind: ProcessQuickKind = methodRequest.processModelNumber === 1 ? 'moderation' : 'mediation'
      setProcessQuickKind(kind)
      setProcessQuickOpen(true)
      setMethodNotice(methodRequest.processModelNumber === 1
        ? '已进入简单调节（PROCESS Model 1）表单。配置 X、W、Y 与推断设置后再复核并手动运行。'
        : '已进入简单中介（PROCESS Model 4）表单。配置 X、M、Y 与推断设置后再复核并手动运行。')
      return
    }
    setProcessQuickOpen(false)
    setMethodNotice(processRequest
      ? '已进入 PROCESS 完整模型库高级编辑器。可使用全部预设、画布和自定义路径；不会自动运行。'
      : `已进入：${methodRequest.label}。请核对模型并冻结版本后手动运行。`)
  }, [methodRequest, onMethodHandled, analysisContext?.contextHash, draftState, editingLocked, model.estimation.family, switchEstimationFamily])

  const [editorSection, setEditorSection] = useState<'variables' | 'paths' | 'estimation'>('variables')
  const [semView, setSemView] = useState<SemView>('full')
  const [collapsedFactors, setCollapsedFactors] = useState<string[]>([])
  const [focusedLatentId, setFocusedLatentId] = useState<string | null>(null)
  const editMeasurement = (id: string) => { setEditorSection('variables'); setFocusedLatentId(id) }

  return (
    <main className="model-builder">
      {methodNotice ? <p className="method-note" role="status">{methodNotice}</p> : null}
      {!processQuickOpen ? (
        <ModelBuilderToolbar
          template={template}
          isCustom={customMode}
          draftState={draftState}
          editingDisabled={editingLocked}
          zenMode={zenMode}
          leftCollapsed={leftCollapsed}
          rightCollapsed={rightCollapsed}
          canUndo={canUndo}
          canRedo={canRedo}
          onUndo={handleUndo}
          onRedo={handleRedo}
          onSelectTemplate={applyTemplate}
          onCreateCustom={startCustomModel}
          onToggleZenMode={() => setZenMode((prev) => !prev)}
          onToggleLeft={() => setLeftCollapsed((prev) => !prev)}
          onToggleRight={() => setRightCollapsed((prev) => !prev)}
          onResetLayout={handleResetLayout}
        />
      ) : null}

      {analysisContext ? <ModelContextBindingBanner analysisContext={analysisContext} blocked={contextGateBlocked} stale={contextBindingStale} /> : null}

      {builderError ? <p className="error-message error-banner" role="alert">{builderError}</p> : null}

      {processQuickOpen ? (
        <ProcessQuickSetupForm
          variables={variables}
          model={model}
          initialKind={processQuickKind}
          disabled={editingLocked}
          onApply={(setup) => {
            const applied = applyProcessQuickSetup(setup)
            if (applied) {
              setProcessQuickOpen(false)
              setMethodNotice('PROCESS 表单配置已应用到当前草稿。请复核路径与估计设置，随后冻结并手动运行。')
            }
            return applied
          }}
          onOpenAdvanced={() => {
            setProcessQuickOpen(false)
            setMethodNotice('已打开高级模型编辑器；当前草稿和既有运行保持不变。')
          }}
        />
      ) : (
        <div className={`model-builder-grid${zenMode ? ' is-zen-mode' : ''}${leftCollapsed ? ' is-left-collapsed' : ''}${rightCollapsed ? ' is-right-collapsed' : ''}`}>
          <ModelVariableLibrary variables={variables} model={model} onAssignVariable={assignVariable} onAddCovariate={addCovariate} onPlaceVariable={addVariableToCanvas} disabled={editingLocked} />

          <div className="model-editor-main">
            {model.estimation.family === 'sem' ? <div className="sem-canvas-toolbar">
              <fieldset aria-label="SEM 模型视图">
                {([['measurement', '测量图'], ['structure', '结构图'], ['full', '完整模型']] as const).map(([view, label]) =>
                  <button key={view} type="button" aria-pressed={semView === view} onClick={() => setSemView(view)}>{label}</button>)}
                <button type="button" onClick={() => setCollapsedFactors([])}>展开全部指标</button>
                <button type="button" onClick={() => setCollapsedFactors((model.latents ?? []).map(latent => latent.id))}>折叠全部指标</button>
              </fieldset>
              <label>定位并编辑测量因子<select disabled={editingLocked} value={focusedLatentId ?? ''} onChange={event => editMeasurement(event.target.value)}>
                <option value="">请选择因子</option>{(model.latents ?? []).map(latent => <option key={latent.id} value={latent.id}>{latent.name}</option>)}
              </select></label>
              <p className="method-note">测量图检查因子–指标关系，结构图编辑回归路径，完整模型同时展示两者。点击“编辑测量”或使用下拉框调整题项；折叠仅影响显示。</p>
            </div> : null}
            <ModelCanvas
              model={model}
              semOptions={model.estimation.family === 'sem' ? {
                view: semView, collapsed: collapsedFactors,
                labels: Object.fromEntries(dataset.variables.map(variable => [variable.id, variable.label])),
                onEdit: editingLocked ? undefined : editMeasurement,
                onToggle: id => setCollapsedFactors(current => current.includes(id) ? current.filter(item => item !== id) : [...current, id]),
              } : undefined}
              pathEvidence={pathEvidence}
              analysisStatus={analysisJob?.status ?? (analysisMutation.isPending ? 'queued' : 'idle')}
              progress={analysisJob?.progress ?? 0}
              statusLabel={recognitionLabel}
              editable={!editingLocked}
              onPositionChange={(nodeId, position) => updateModel((current) => ({
                ...current,
                canvas: { positions: { ...current.canvas?.positions, [model.estimation.family === 'sem' && semView !== 'structure' ? `sem:${nodeId}` : nodeId]: position } },
              }))}
              onConnect={handleConnect}
              onReconnectEdge={reconnectEdge}
              onDropVariable={addVariableToCanvas}
              onDeleteNode={removeCanvasNode}
              onChangeNodeRole={changeNodeRole}
              onDeleteEdges={(edgeIds) => updateModel((current) => removeModelEdges(current, edgeIds))}
            />

            <nav className="process-editor-tabs" aria-label="模型编辑分区">
              <button type="button" aria-pressed={editorSection === 'variables'} onClick={() => setEditorSection('variables')}>1 · 变量与控制</button>
              <button type="button" aria-pressed={editorSection === 'paths'} onClick={() => setEditorSection('paths')}>2 · 路径与调节</button>
              <button type="button" aria-pressed={editorSection === 'estimation'} onClick={() => setEditorSection('estimation')}>3 · 估计设置</button>
            </nav>
            <fieldset className="process-editing-fields" disabled={editingLocked}>
              <legend className="sr-only">当前模型设置</legend>
              <div hidden={editorSection !== 'variables'}>
                {model.estimation.family === 'sem' ? <SemStudioMeasurementEditor model={model} indicatorCandidates={indicatorCandidates} updateModel={updateModel} focusedLatentId={focusedLatentId} /> : null}
                <RoleEditorSection model={model} variables={variables} onAssignVariable={assignVariable} onAddStructuralNode={addStructuralNode} onRemoveStructuralNode={removeStructuralNode} onChangeNodeRole={changeNodeRole} onRenameNode={(id, label) => updateModel(current => ({ ...current, nodes: current.nodes.map(node => node.id === id ? { ...node, label } : node) }))} />
                <CovariateEditor model={model} variables={variables} unusedVariables={unusedVariables} onAdd={addCovariate} onChange={(updated) => updateModel(() => updated)} />
              </div>
              <div hidden={editorSection !== 'paths'}>
                <PathEditorSection model={model} onAddEdge={addEdge} onUpdateModel={updateModel} />
                <ModerationEditor model={model} onChange={(moderations) => updateModel((current) => ({ ...current, moderations }))} />
              </div>
              <div hidden={editorSection !== 'estimation'}>
                <ModelEstimationEditor model={model} variables={variables} indicatorCandidates={indicatorCandidates} updateModel={updateModel} onSwitchEstimationFamily={switchEstimationFamily} />
              </div>
            </fieldset>
          </div>

          <ModelBuilderSidebar
            model={model}
            validation={validation}
            freezeMutation={freezeMutation}
            overrideReason={overrideReason}
            setOverrideReason={setOverrideReason}
            contextGateBlocked={contextGateBlocked}
            contextBindingStale={contextBindingStale}
            analysisRunning={analysisRunning}
            analysisMutation={analysisMutation}
            analysisJob={analysisJob}
            cancelMutation={cancelMutation}
          />
        </div>
      )}

      {analysisResult ? (
        <ResultPanel
          result={analysisResult}
          isRunning={analysisRunning}
          title={`${analysisResult.semResult ? 'SEM' : analysisResult.run.template?.replace('model_', 'PROCESS Model ') ?? 'PROCESS'} · 本次结果`}
        />
      ) : null}
    </main>
  )
}
