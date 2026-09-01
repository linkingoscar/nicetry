import type { EmpiricalAnalysisReport } from './datasets'

export type EmpiricalResultAvailability = 'available' | 'unavailable' | 'not_requested'

export interface EmpiricalAnalysisSegmentMap {
  summary: Pick<
    EmpiricalAnalysisReport,
    | 'reliability'
    | 'sample'
    | 'missingDataReport'
    | 'descriptives'
    | 'frequencies'
    | 'commonMethodBias'
    | 'factorability'
    | 'academicInterpretation'
    | 'apaTables'
    | 'publicationEligible'
    | 'requiresManualReview'
    | 'publicationEligibilityReasons'
    | 'sampleFlow'
  > & {
    resultAvailability: Record<
      'groups' | 'regression' | 'advanced' | 'longitudinal' | 'diary',
      EmpiricalResultAvailability
    >
    efa: Pick<EmpiricalAnalysisReport['efa'], 'factorCount'>
    cfa: Pick<
      EmpiricalAnalysisReport['cfa'],
      'available' | 'reason' | 'validForConfirmatoryInterpretation'
    >
  }
  correlation: Pick<EmpiricalAnalysisReport, 'correlations' | 'paperSummaryTable'>
  efa_cfa: Pick<EmpiricalAnalysisReport, 'efa' | 'cfa' | 'advancedMeasurementBoundary'>
  validity: Pick<EmpiricalAnalysisReport, 'validity' | 'measurementInvariance'>
  regression: Pick<
    EmpiricalAnalysisReport,
    'groupComparison' | 'aggregationDiagnostics' | 'hierarchicalRegression' | 'responseSurface' | 'multiplicity'
  >
  longitudinal: Pick<EmpiricalAnalysisReport, 'longitudinalPanel' | 'diaryMultilevel'>
}
