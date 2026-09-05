import { useQuery } from '@tanstack/react-query'

import { getEmpiricalSegment } from '../api/empirical-analysis'
import type { EmpiricalAnalysisOptions } from '../types'
import { EmpiricalProcedureResultView } from './empirical/EmpiricalProcedureResult'

interface OutputEmpiricalRunPreviewProps {
  datasetId: string
  measurementVersion: number | null
  reportId: string
  options: EmpiricalAnalysisOptions
}

const SUMMARY_PROCEDURES = new Set([
  'descriptives',
  'frequencies',
  'missing',
  'reliability',
  'common_method',
  'efa',
  'cfa',
  'validity',
])
const MEASUREMENT_PROCEDURES = new Set(['efa', 'cfa', 'validity'])
const REGRESSION_PROCEDURES = new Set([
  'groups',
  'aggregation',
  'regression',
  'relative_importance',
  'response_surface',
])

export function OutputEmpiricalRunPreview({
  datasetId,
  measurementVersion,
  reportId,
  options,
}: OutputEmpiricalRunPreviewProps) {
  const procedure = options.procedure
  const needsSummary = procedure ? SUMMARY_PROCEDURES.has(procedure) : false
  const needsCorrelation = procedure === 'correlation'
  const needsMeasurement = procedure ? MEASUREMENT_PROCEDURES.has(procedure) : false
  const needsValidity = procedure === 'validity' || procedure === 'invariance'
  const needsRegression = procedure ? REGRESSION_PROCEDURES.has(procedure) : false

  const summaryQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'summary'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'summary'),
    enabled: needsSummary,
    staleTime: Infinity,
  })
  const correlationQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'correlation'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'correlation'),
    enabled: needsCorrelation,
    staleTime: Infinity,
  })
  const measurementQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'efa_cfa'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'efa_cfa'),
    enabled: needsMeasurement,
    staleTime: Infinity,
  })
  const validityQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'validity'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'validity'),
    enabled: needsValidity,
    staleTime: Infinity,
  })
  const regressionQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'regression'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'regression'),
    enabled: needsRegression,
    staleTime: Infinity,
  })

  if (!procedure) return <p className="muted">该运行没有记录方法身份，无法选择只读结果分区。</p>

  return (
    <section className="output-run-preview" aria-label="只读结果预览">
      <div className="section-heading-row">
        <div>
          <p className="eyebrow">只读结果</p>
          <h3>本次运行结果</h3>
        </div>
      </div>
      <EmpiricalProcedureResultView
        reportId={reportId}
        reportOptions={options}
        datasetId={datasetId}
        measurementVersion={measurementVersion}
        queries={{
          summary: summaryQuery,
          correlation: correlationQuery,
          efaCfa: measurementQuery,
          validity: validityQuery,
          regression: regressionQuery,
        }}
        showToast={() => undefined}
      />
    </section>
  )
}
