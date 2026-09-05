import { createContext, useContext, type ReactNode, type RefObject } from 'react'
import type {
  AnalysisSampleVersion,
  EmpiricalAnalysisJob,
  MeasurementVersion,
} from '../../types'
import type { EmpiricalConfigValue } from './EmpiricalAnalysisConfig'
import type { LongitudinalItemGroup } from './LongitudinalPanelConfig'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'
import type { AnalysisParadigm } from '../../types/study-context'
import type { DatasetRoleBindings } from '../../types/analysis-context'
import type { SegmentQueryState } from './segmentQuery'
import type { EmpiricalAnalysisSegmentMap } from '../../types'

export interface Candidate {
  id: string
  label: string
}

export interface EmpiricalAnalysisContextValue {
  procedures: import('./empiricalProcedures').ProcedureDefinition[]
  capabilitiesLoading: boolean
  capabilitiesError: boolean
  analysisCandidates: Candidate[]
  allCandidates: Candidate[]
  onSelectProcedure: (procedure: import('../../types/empirical-types').EmpiricalProcedure) => void
  runHistory: import('./empiricalRunHistory').EmpiricalRunEntry[]
  onSelectRun: (id: string) => void
  activeRunId: string | null
  measurement: MeasurementVersion | null
  scores: Candidate[]
  groupCandidates: Candidate[]
  aggregationCandidates: Candidate[]
  controlCandidates: Candidate[]
  longitudinalCandidates: Candidate[]
  longitudinalItemGroups: LongitudinalItemGroup[]
  subjectCandidates: Candidate[]
  contextRoles?: DatasetRoleBindings | null
  nestedContext: boolean
  sampleVersions?: AnalysisSampleVersion[]
  config: EmpiricalConfigValue
  researchParadigm: AnalysisParadigm
  configExpanded: boolean
  hasReport: boolean
  isRunning: boolean
  analysisJob?: EmpiricalAnalysisJob
  cancelPending: boolean
  error: string | null
  draftSaveStatus: 'local' | 'saving' | 'saved' | 'conflict' | 'failed'
  onConfigChange: (patch: Partial<EmpiricalConfigValue>) => void
  onToggleExpanded: () => void
  onRun: () => void
  onCancel: (runId: string) => void
  report?: EmpiricalAnalysisJob | null
  isConfigStale: boolean
  isContextStale: boolean
  datasetId: string
  datasetName: string
  measurementVersion: number | null
  summaryQuery: SegmentQueryState<EmpiricalAnalysisSegmentMap['summary']>
  correlationQuery: SegmentQueryState<EmpiricalAnalysisSegmentMap['correlation']>
  efaCfaQuery: SegmentQueryState<EmpiricalAnalysisSegmentMap['efa_cfa']>
  validityQuery: SegmentQueryState<EmpiricalAnalysisSegmentMap['validity']>
  regressionQuery: SegmentQueryState<EmpiricalAnalysisSegmentMap['regression']>
  activeTab: EmpiricalResultTab
  isPending: boolean
  setActiveTab: (tab: EmpiricalResultTab) => void
  resultStatus: (key: 'groups' | 'regression' | 'advanced' | 'longitudinal' | 'diary') => 'available' | 'warning' | 'not_requested'
  showToast: (msg: string) => void
  toastText: string | null
  resultsRef: RefObject<HTMLDivElement | null>
}

const EmpiricalAnalysisContext = createContext<EmpiricalAnalysisContextValue | null>(null)

export function EmpiricalAnalysisProvider({
  value,
  children,
}: {
  value: EmpiricalAnalysisContextValue
  children: ReactNode
}) {
  return (
    <EmpiricalAnalysisContext.Provider value={value}>
      {children}
    </EmpiricalAnalysisContext.Provider>
  )
}

export function useEmpiricalAnalysisContext(): EmpiricalAnalysisContextValue {
  const value = useContext(EmpiricalAnalysisContext)
  if (!value) {
    throw new Error('useEmpiricalAnalysisContext must be used inside EmpiricalAnalysisProvider')
  }
  return value
}
