import { lazy, Suspense, useState } from 'react'
import type { MethodRequest } from './components/context/workbenchNavigation'

import { AppHydratingScreen } from './AppHydratingScreen'
import { AppWorkspaceTabs } from './AppWorkspaceTabs'
import { DataWorkspace } from './components/DataWorkspace'
import { CommandPalette } from './components/shared/CommandPalette'
import { LocalPrivacyBadge } from './components/shared/LocalPrivacyBadge'
import { ResearchStart } from './components/shared/ResearchStart'
import { StudyContextSwitcher } from './components/shared/StudyContextSwitcher'
import { SectionErrorBoundary } from './components/shared/SectionErrorBoundary'
import { ToastContainer } from './components/shared/Toast'
import { useTheme } from './hooks/useTheme'
import { useWorkspaceState } from './hooks/useWorkspaceState'

const EmpiricalAnalysis = lazy(() => import('./components/EmpiricalAnalysis').then((module) => ({ default: module.EmpiricalAnalysis })))
const ModelBuilder = lazy(() => import('./components/ModelBuilder').then((module) => ({ default: module.ModelBuilder })))
const ContextCapabilityCatalog = lazy(() => import('./components/context/ContextCapabilityCatalog').then((module) => ({ default: module.ContextCapabilityCatalog })))
const PlanningWorkspace = lazy(() => import('./components/PlanningWorkspace').then((module) => ({ default: module.PlanningWorkspace })))

export function App() {
  const { theme, setTheme } = useTheme()
  const [modelMethodRequest, setModelMethodRequest] = useState<MethodRequest | null>(null)
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
          {studyIntent === 'analyze' ? <button
            type="button"
            className="command-palette-trigger"
            onClick={() => setIsCommandPaletteOpen(true)}
          >
            <span>搜索 / 命令</span>
            <kbd>Ctrl+K</kbd>
          </button> : null}
          {studyIntent ? <button type="button" className="header-path-button" onClick={handleReturnToStart}>重新选择路径</button> : null}
          <LocalPrivacyBadge datasetName={activeDataset?.originalFile.name} datasetSha256={activeDataset?.originalFile.sha256} />
        </div>
      </header>

      {studyIntent === null ? (
        <main className="start-shell">
          <ResearchStart onSelect={handleIntentSelect} />
        </main>
      ) : null}

      {studyIntent === 'plan' ? (
        <Suspense fallback={<main className="centered-state" aria-live="polite"><p>正在加载规划工作台…</p></main>}>
          <SectionErrorBoundary resetKey="planning-view" title="方案规划与准入诊断">
            <PlanningWorkspace
              context={effectiveStudyContext}
              onContextChange={handleStudyContextChange}
              datasetId={activeDataset?.id}
              datasetVariables={activeDataset?.variables}
            />
          </SectionErrorBoundary>
        </Suspense>
      ) : null}

      {studyIntent === 'analyze' ? (
        <section className="context-banner">
          <StudyContextSwitcher
            value={effectiveStudyContext}
            hasDataset={Boolean(activeDataset)}
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
          onSelect={setActiveView}
        />
      ) : null}

      {studyIntent === 'analyze' ? <div
        role="tabpanel"
        id={`workspace-panel-${activeView}`}
        aria-labelledby={`workspace-tab-${activeView}`}
      >
        <Suspense fallback={<main className="centered-state" aria-live="polite"><p>正在加载分析模块…</p></main>}>
          {activeView === 'data' && studyIntent === 'analyze' ? (
          <SectionErrorBoundary resetKey="data-view" title="数据与测量准备">
            <DataWorkspace
              activeDataset={activeDataset}
              activeMeasurement={modelContext?.measurement}
              onDatasetReady={handleDatasetReady}
              onClearWorkspace={() => { const cleared = handleClearWorkspace(); if (cleared) setModelMethodRequest(null); return cleared }}
              onMeasurementReady={handleMeasurementReady}
              onStructureSaved={handleStructureSaved}
              onContinueToAnalysis={() => setActiveView('empirical')}
              onLoadDemo={handleLoadDemo}
              loadingDemo={loadingDemo}
              studyContext={effectiveStudyContext}
              resolvedContext={resolvedContext}
            />
          </SectionErrorBoundary>
        ) : activeView === 'empirical' && activeDataset?.dictionary.status === 'confirmed' && resolvedContext?.validity === 'ready' ? (
          <SectionErrorBoundary resetKey="empirical-view" title="问卷实证分析区">
            <EmpiricalAnalysis
              key={`${activeDataset.id}:${activeDataset.dictionary.version}:${modelContext?.measurement.version ?? 'raw'}:${resolvedContext.contextHash}`}
              dataset={activeDataset}
              measurement={modelContext?.measurement ?? null}
              researchParadigm={researchParadigm}
              analysisContext={resolvedContext}
              tabRequest={empiricalTabRequest ?? undefined}
            />
          </SectionErrorBoundary>
        ) : activeView === 'model' && modelContext && resolvedContext?.validity === 'ready' ? (
          <SectionErrorBoundary resetKey="model-view" title="PROCESS 模型构建与估计">
            <ModelBuilder dataset={modelContext.dataset} measurement={modelContext.measurement} analysisContext={resolvedContext} methodRequest={modelMethodRequest} onMethodHandled={() => setModelMethodRequest(null)} />
          </SectionErrorBoundary>
        ) : activeView === 'methods' && activeDataset && resolvedContext ? (
          <SectionErrorBoundary resetKey="context-methods-view" title="当前研究上下文可用方法">
            <ContextCapabilityCatalog
              context={resolvedContext}
              variables={activeDataset.variables}
              onPrepare={() => setActiveView('data')}
              onNavigate={({ view, tab, sliceId, label }) => {
                const method = { sliceId, label, contextHash: resolvedContext.contextHash, key: Date.now() }
                if (view === 'model') setModelMethodRequest(method)
                setActiveView(view)
                if (tab) {
                  setEmpiricalTabRequest({
                    tab,
                    key: method.key,
                    method,
                  })
                }
              }}
            />
          </SectionErrorBoundary>
        ) : activeView === 'methods' && activeDataset ? (
          <main className="centered-state" aria-live="polite"><p>{resolvedContextQuery.isError ? '当前分析上下文读取失败，请刷新后重试。' : '正在解析当前分析上下文…'}</p></main>
        ) : (activeView === 'empirical' || activeView === 'model') && activeDataset ? (
          <main className="centered-state" aria-live="polite">
            <p>
              当前研究上下文尚未就绪{resolvedContext?.missingRequirements?.length ? `：还缺少 ${resolvedContext.missingRequirements.join('、')}` : ''}；请回到数据页重新确认结构、测量与版本绑定后再运行分析。
            </p>
            <button type="button" className="secondary-button" onClick={() => setActiveView('data')}>返回数据准备</button>
          </main>
        ) : (
          <main className="centered-state">
            <p>请先导入数据、确认变量并完成构念计分。</p>
            <button
              type="button"
              className="run-button"
              disabled={loadingDemo}
              onClick={handleLoadDemo}
            >
              {loadingDemo ? '正在加载时间结构示例项目...' : '一键加载当前时间结构示例项目'}
            </button>
          </main>
          )}
        </Suspense>
      </div> : null}

      {studyIntent === 'analyze' ? (
        <CommandPalette
          isOpen={isCommandPaletteOpen}
          onClose={() => setIsCommandPaletteOpen(false)}
          onSelectView={(view) => setActiveView(view)}
          onSelectEmpiricalTab={(tab) =>
            setEmpiricalTabRequest({
              tab,
              key: Date.now(),
            })
          }
          onLoadDemo={handleLoadDemo}
          variables={
            modelContext?.measurement?.constructs.flatMap((construct) =>
              construct.itemIds.map((itemId) => ({ id: itemId, label: itemId })),
            ) ??
            activeDataset?.variables?.map((v) => ({ id: v.id, label: v.label })) ??
            []
          }
        />
      ) : null}
      <ToastContainer />
    </div>
  )
}
