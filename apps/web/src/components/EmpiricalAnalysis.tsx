import type { EmpiricalTabRequest } from './context/workbenchNavigation'
import type {
  DatasetVersion,
  MeasurementVersion,
} from '../types'
import type { AnalysisParadigm } from '../types/study-context'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
import { useEmpiricalAnalysisState } from './empirical/useEmpiricalAnalysisState'
import { EmpiricalAnalysisProvider } from './empirical/EmpiricalAnalysisContext'
import { EmpiricalAnalysisShellHeader } from './empirical/EmpiricalAnalysisShellHeader'
import { EmpiricalProcedureMenu } from './empirical/EmpiricalProcedureMenu'
import { EmpiricalResultsSection } from './empirical/EmpiricalResultsSection'

interface EmpiricalAnalysisProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  tabRequest?: EmpiricalTabRequest
  researchParadigm?: AnalysisParadigm
  analysisContext?: ResolvedAnalysisContext | null
}

export function EmpiricalAnalysis({
  dataset,
  measurement,
  tabRequest,
  researchParadigm = 'questionnaire',
  analysisContext,
}: EmpiricalAnalysisProps) {
  const state = useEmpiricalAnalysisState({
    dataset,
    measurement,
    tabRequest,
    researchParadigm,
    analysisContext,
  })

  return (
    <EmpiricalAnalysisProvider value={state}>
      <main className="empirical-center">
        <p className="method-note">配置按数据、测量版本、研究上下文和具体方法分别保存；上游版本变化后使用新草稿，旧任务不会自动重新估计。</p>
        <div className="empirical-procedure-workspace">
          <EmpiricalProcedureMenu />
          <div className="procedure-main"><EmpiricalAnalysisShellHeader /><EmpiricalResultsSection /></div>
        </div>
        {state.toastText && <div className="toast-notification" role="status"><span>{state.toastText}</span></div>}
      </main>
    </EmpiricalAnalysisProvider>
  )
}
