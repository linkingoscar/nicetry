import type { EmpiricalTabRequest } from './context/workbenchNavigation'
import type {
  DatasetVersion,
  MeasurementVersion,
} from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import type { AnalysisParadigm } from '../types/study-context'
import type { ResolvedAnalysisContext } from '../types/analysis-context'
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
  useEmpiricalAnalysisIndexSync(dataset, measurement, state.analysisJob)

  return (
    <EmpiricalAnalysisProvider value={state}>
      <main className="empirical-center">
        <p className="method-note">当前方法由统一方法库进入。配置按分析对象和上游版本分别保存；上游变化不会自动重算或覆盖旧结果。</p>
        <div className="procedure-main"><EmpiricalAnalysisShellHeader /><EmpiricalResultsSection /></div>
        {state.toastText && <div className="toast-notification" role="status"><span>{state.toastText}</span></div>}
      </main>
    </EmpiricalAnalysisProvider>
  )
}
