import { lazy, Suspense, useState } from 'react'
import type { EmpiricalProcedure } from './types/empirical-types'
import type { MethodRequest } from './components/context/workbenchNavigation'

import { AppHydratingScreen } from './AppHydratingScreen'
import { AppWorkspaceTabs } from './AppWorkspaceTabs'
import { DataWorkspace } from './components/DataWorkspace'
import { OutputWorkspace } from './components/OutputWorkspace'
import { CommandPalette } from './components/shared/CommandPalette'
import { LocalPrivacyBadge } from './components/shared/LocalPrivacyBadge'
import { ResearchStart } from './components/shared/ResearchStart'
import { StudyContextSwitcher } from './components/shared/StudyContextSwitcher'
import { SectionErrorBoundary } from './components/shared/SectionErrorBoundary'
import { ToastContainer } from './components/shared/Toast'
import { procedureDefinition } from './components/empirical/empiricalProcedures'
import { useTheme } from './hooks/useTheme'
import { useWorkspaceState } from './hooks/useWorkspaceState'

const EmpiricalAnalysis = lazy(() => import('./components/EmpiricalAnalysis').then((module) => ({ default: module.EmpiricalAnalysis })))
const ModelBuilder = lazy(() => import('./components/ModelBuilder').then((module) => ({ default: module.ModelBuilder })))
const ContextCapabilityCatalog = lazy(() => import('./components/context/ContextCapabilityCatalog').then((module) => ({ default: module.ContextCapabilityCatalog })))
const PlanningWorkspace = lazy(() => import('./components/PlanningWorkspace').then((module) => ({ default: module.PlanningWorkspace })))

type AnalysisSurface = 'library' | 'empirical' | 'model'

export function App() {
  const { theme, setTheme } = useTheme()
  const [modelMethodRequest, setModelMethodRequest] = useState<MethodRequest | null>(null)
  const [analysisSurface, setAnalysisSurface] = useState<AnalysisSurface>('library')
  const {
    workspaceNavRef,
    studyIntent,
    effectiveStudyContext,
    studyContextSaveError,
    studyContextPersistence,
    activeView,
    setActiveView,
    loadingDemo,
    activeDataset,
    modelContext,
    hydrating,
    isCommandPaletteOpen,
    setIsCommandPaletteOpen,
    empiricalTabRequest,
    setEmpiricalTabRequest,
    resolvedContextQuery,
    resolvedContext,
    researchParadigm,
    workspaceSteps,
    handleMeasurementReady,
    handleDatasetReady,
    handleStructureSaved,
    handleLoadDemo,
    handleIntentSelect,
    handleStudyContextChange,
    handleReturnToStart,
    handleClearWorkspace,
  } = useWorkspaceState()

  if (hydrating && !activeDataset) return <AppHydratingScreen />

  const openEmpiricalProcedure = (procedure: EmpiricalProcedure) => {
    const definition = procedureDefinition(procedure)
    const method = {
      sliceId: definition.slice,
      label: definition.label,
      contextHash: resolvedContext?.contextHash ?? '',
      key: Date.now(),
    }
    setEmpiricalTabRequest({ tab: definition.tab, key: method.key, method })
    setAnalysisSurface('empirical')
    setActiveView('analyze')
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <p className="brand">研径 <span>ResearchPath</span></p>
          <p className="project-name">{activeDataset?.originalFile.name ?? '本地实证研究工作台'}</p>
        </div>
        <div className="header-meta">
          <button
            type="button"
            className="theme-toggle-button"
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
          >
            <span>{theme === 'dark' ? '暗色模式' : '明亮模式'}</span>
          </button>
          {studyIntent === 'analyze' ? (
            <button type="button" className="command-palette-trigger" onClick={() => setIsCommandPaletteOpen(true)}>
              <span>搜索 / 命令</span>
              <kbd>Ctrl+K</kbd>
            </button>
          ) : null}
          {studyIntent ? <button type="button" className="header-path-button" onClick={handleReturnToStart}>项目首页</button> : null}
          <LocalPrivacyBadge datasetName={activeDataset?.originalFile.name} datasetSha256={activeDataset?.originalFile.sha256} />
        </div>
      </header>

      {studyIntent === null ? (
        <main className="start-shell">
          <ResearchStart onSelect={handleIntentSelect} />
        </main>
      ) : null}

      {studyIntent === 'plan' ? (
        <Suspense fallback={<main className="centered-state" aria-live="polite"><p>正在加载规划工具…</p></main>}>
          <SectionErrorBoundary resetKey="planning-view" title="功效与研究规划">
            <PlanningWorkspace
              context={effectiveStudyContext}
              onContextChange={handleStudyContextChange}
              datasetId={activeDataset?.id}
              datasetVariables={activeDataset?.variables}
            />
          </SectionErrorBoundary>
        </Suspense>
      ) : null}

      {studyIntent === 'analyze' && activeDataset ? (
        <section className="context-banner">
          <StudyContextSwitcher
            value={effectiveStudyContext}
            hasDataset
            persistence={studyContextPersistence}
            onChange={handleStudyContextChange}
          />
          {studyContextSaveError ? <p className="context-save-error" role="alert">{studyContextSaveError}</p> : null}
        </section>
      ) : null}

      {studyIntent === 'analyze' ? (
        <AppWorkspaceTabs
          navRef={workspaceNavRef}
          workspaceSteps={workspaceSteps}
          activeView={activeView}
          onSelect={(view) => {
            setActiveView(view)
            if (view === 'analyze') setAnalysisSurface('library')
          }}
        />
      ) : null}

      {studyIntent === 'analyze' ? (
        <div role="tabpanel" id={`workspace-panel-${activeView}`} aria-labelledby={`workspace-tab-${activeView}`}>
          <Suspense fallback={<main className="centered-state" aria-live="polite"><p>正在加载工作区…</p></main>}>
            {activeView === 'data' ? (
              <SectionErrorBoundary resetKey="data-view" title="数据">
                <DataWorkspace
                  activeDataset={activeDataset}
                  activeMeasurement={modelContext?.measurement}
                  onDatasetReady={handleDatasetReady}
                  onClearWorkspace={() => {
                    const cleared = handleClearWorkspace()
                    if (cleared) {
                      setModelMethodRequest(null)
                      setAnalysisSurface('library')
                    }
                    return cleared
                  }}
                  onMeasurementReady={handleMeasurementReady}
                  onStructureSaved={handleStructureSaved}
                  onContinueToAnalysis={() => {
                    setAnalysisSurface('library')
                    setActiveView('analyze')
                  }}
                  onLoadDemo={handleLoadDemo}
                  loadingDemo={loadingDemo}
                  studyContext={effectiveStudyContext}
                  resolvedContext={resolvedContext}
                />
              </SectionErrorBoundary>
            ) : activeView === 'analyze' && !activeDataset ? (
              <main className="centered-state">
                <h2>请先导入数据</h2>
                <p>有活动数据后即可进入统一方法库；不需要先完成全部变量、量表或研究结构确认。</p>
                <button type="button" className="secondary-button" onClick={() => setActiveView('data')}>返回数据</button>
              </main>
            ) : activeView === 'analyze' && analysisSurface === 'empirical' && activeDataset && resolvedContext ? (
              <SectionErrorBoundary resetKey="empirical-view" title="分析">
                <div className="analysis-shell">
                  <button type="button" className="secondary-button" onClick={() => setAnalysisSurface('library')}>← 返回方法库</button>
                  <EmpiricalAnalysis
                    key={`${activeDataset.id}:${activeDataset.dictionary.version}:${modelContext?.measurement.version ?? 'raw'}:${resolvedContext.contextHash}`}
                    dataset={activeDataset}
                    measurement={modelContext?.measurement ?? null}
                    researchParadigm={researchParadigm}
                    analysisContext={resolvedContext}
                    tabRequest={empiricalTabRequest ?? undefined}
                  />
                </div>
              </SectionErrorBoundary>
            ) : activeView === 'analyze' && analysisSurface === 'model' && modelContext && resolvedContext ? (
              <SectionErrorBoundary resetKey="model-view" title="高级模型编辑器">
                <div className="analysis-shell">
                  <button type="button" className="secondary-button" onClick={() => setAnalysisSurface('library')}>← 返回方法库</button>
                  <ModelBuilder
                    dataset={modelContext.dataset}
                    measurement={modelContext.measurement}
                    analysisContext={resolvedContext}
                    methodRequest={modelMethodRequest}
                    onMethodHandled={() => setModelMethodRequest(null)}
                  />
                </div>
              </SectionErrorBoundary>
            ) : activeView === 'analyze' && analysisSurface === 'model' && activeDataset ? (
              <main className="centered-state">
                <h2>该模型还需要量表/测量设置</h2>
                <p>高级 PROCESS/SEM 编辑器继续保留，但只在满足当前模型实际前提后打开。你可以先回方法库选择无需量表的分析。</p>
                <button type="button" className="secondary-button" onClick={() => setAnalysisSurface('library')}>返回方法库</button>
              </main>
            ) : activeView === 'analyze' && activeDataset && resolvedContext ? (
              <SectionErrorBoundary resetKey="context-methods-view" title="分析方法库">
                <ContextCapabilityCatalog
                  context={resolvedContext}
                  variables={activeDataset.variables}
                  onPrepare={() => setActiveView('data')}
                  onNavigate={({ view, tab, sliceId, label }) => {
                    const method = { sliceId, label, contextHash: resolvedContext.contextHash, key: Date.now() }
                    if (view === 'model') {
                      setModelMethodRequest(method)
                      setAnalysisSurface('model')
                    } else {
                      setAnalysisSurface('empirical')
                    }
                    if (tab) setEmpiricalTabRequest({ tab, key: method.key, method })
                  }}
                />
              </SectionErrorBoundary>
            ) : activeView === 'analyze' && activeDataset ? (
              <main className="centered-state" aria-live="polite">
                <h2>分析方法库正在准备</h2>
                <p>{resolvedContextQuery.isError ? '当前分析上下文读取失败。你仍可返回数据查看或修改当前数据结构。' : '正在读取当前数据的最小分析条件…'}</p>
                <button type="button" className="secondary-button" onClick={() => setActiveView('data')}>查看数据</button>
              </main>
            ) : activeView === 'output' && activeDataset ? (
              <SectionErrorBoundary resetKey="output-view" title="输出">
                <OutputWorkspace dataset={activeDataset} measurement={modelContext?.measurement ?? null} onOpenProcedure={openEmpiricalProcedure} />
              </SectionErrorBoundary>
            ) : activeView === 'output' ? (
              <main className="centered-state">
                <h2>还没有活动数据</h2>
                <p>导入数据并运行分析后，结果会集中显示在输出工作区。</p>
                <button type="button" className="secondary-button" onClick={() => setActiveView('data')}>导入数据</button>
              </main>
            ) : null}
          </Suspense>
        </div>
      ) : null}

      {studyIntent === 'analyze' ? (
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
          onSelectView={(view) => {
            setActiveView(view)
            if (view === 'analyze') setAnalysisSurface('library')
          }}
          onSelectEmpiricalTab={(tab) => {
            setAnalysisSurface('empirical')
            setEmpiricalTabRequest({ tab, key: Date.now() })
          }}
          onLoadDemo={handleLoadDemo}
          variables={
            modelContext?.measurement?.constructs.flatMap((construct) =>
              construct.itemIds.map((itemId) => ({ id: itemId, label: itemId })),
            ) ?? activeDataset?.variables?.map((v) => ({ id: v.id, label: v.label })) ?? []
          }
        />
      ) : null}
      <ToastContainer />
    </div>
  )
}
