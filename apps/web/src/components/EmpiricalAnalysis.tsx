import { useEffect, useState } from 'react'
import type { EmpiricalTabRequest } from './context/workbenchNavigation'
import type {
  DatasetVersion,
  MeasurementVersion,
} from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import type { AnalysisParadigm } from '../types/study-context'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import {
  loadEmpiricalAnalysisIndex,
  updateAnalysisDocumentMetadata,
} from './analyses/analysisDocuments'
import { useEmpiricalAnalysisIndexSync } from './analyses/useEmpiricalAnalysisIndexSync'
import { useEmpiricalAnalysisState } from './empirical/useEmpiricalAnalysisState'
import { EmpiricalAnalysisProvider } from './empirical/EmpiricalAnalysisContext'
import { EmpiricalAnalysisShellHeader } from './empirical/EmpiricalAnalysisShellHeader'
import { EmpiricalResultsSection } from './empirical/EmpiricalResultsSection'

interface EmpiricalAnalysisProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  tabRequest?: EmpiricalTabRequest
  researchParadigm?: AnalysisParadigm
  analysisContext?: ResolvedAnalysisContext | null
  analysisId?: string | null
  analysisProcedure?: EmpiricalProcedure
}

export function EmpiricalAnalysis({
  dataset,
  measurement,
  tabRequest,
  researchParadigm = 'questionnaire',
  analysisContext,
  analysisId,
  analysisProcedure,
}: EmpiricalAnalysisProps) {
  const state = useEmpiricalAnalysisState({
    dataset,
    measurement,
    tabRequest,
    researchParadigm,
    analysisContext,
    analysisId,
    analysisProcedure,
  })
  const [analysisTitle, setAnalysisTitle] = useState<string | null>(null)

  useEmpiricalAnalysisIndexSync(dataset, measurement, state.analysisJob)

  useEffect(() => {
    if (!analysisId) {
      setAnalysisTitle(null)
      return
    }
    const document = loadEmpiricalAnalysisIndex(dataset, measurement).documents.find((entry) => entry.id === analysisId)
    setAnalysisTitle(document?.title ?? null)
  }, [analysisId, dataset, measurement])

  const renameAnalysis = () => {
    if (!analysisId) return
    const nextTitle = window.prompt('分析名称', analysisTitle ?? analysisProcedure ?? '分析')
    if (nextTitle === null) return
    const title = nextTitle.trim()
    if (!title) return
    const index = updateAnalysisDocumentMetadata(dataset.projectId, analysisId, { title })
    const updated = index.documents.find((entry) => entry.id === analysisId)
    if (!updated) return
    setAnalysisTitle(updated.title)
    state.showToast(`已重命名为“${updated.title}”。`)
  }

  return (
    <EmpiricalAnalysisProvider value={state}>
      <main className="empirical-center">
        {analysisId ? (
          <section className="method-note" aria-label="当前分析">
            <strong>{analysisTitle ?? '当前分析'}</strong>
            <span> · 独立分析对象</span>
            <button type="button" className="text-button" onClick={renameAnalysis}>重命名</button>
          </section>
        ) : null}
        <p className="method-note">当前方法由统一方法库进入。配置按分析对象和上游版本分别保存；上游变化不会自动重算或覆盖旧结果。</p>
        <div className="procedure-main"><EmpiricalAnalysisShellHeader /><EmpiricalResultsSection /></div>
        {state.toastText && <div className="toast-notification" role="status"><span>{state.toastText}</span></div>}
      </main>
    </EmpiricalAnalysisProvider>
  )
}
