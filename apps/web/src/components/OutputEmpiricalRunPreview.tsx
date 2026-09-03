import { useQuery } from '@tanstack/react-query'

import { getEmpiricalSegment } from '../api/empirical-analysis'
import type { EmpiricalAnalysisOptions } from '../types'
import { EmpiricalCorrelationTab } from './empirical/EmpiricalCorrelationTab'
import { EmpiricalOverviewTab } from './empirical/EmpiricalOverviewTab'

interface OutputEmpiricalRunPreviewProps {
  datasetId: string
  measurementVersion: number | null
  reportId: string
  options: EmpiricalAnalysisOptions
}

const SUMMARY_PROCEDURES = new Set(['descriptives', 'frequencies', 'missing'])

export function OutputEmpiricalRunPreview({
  datasetId,
  measurementVersion,
  reportId,
  options,
}: OutputEmpiricalRunPreviewProps) {
  const procedure = options.procedure
  const showSummary = Boolean(procedure && SUMMARY_PROCEDURES.has(procedure))
  const showCorrelation = procedure === 'correlation'

  const summaryQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'summary'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'summary'),
    enabled: showSummary,
    staleTime: Infinity,
  })
  const correlationQuery = useQuery({
    queryKey: ['output-empirical-segment', datasetId, measurementVersion, reportId, 'correlation'],
    queryFn: () => getEmpiricalSegment(datasetId, measurementVersion, reportId, 'correlation'),
    enabled: showCorrelation,
    staleTime: Infinity,
  })

  if (showSummary) {
    return (
      <section className="output-run-preview" aria-label="只读结果预览">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">只读结果</p>
            <h3>本次运行结果预览</h3>
          </div>
        </div>
        <EmpiricalOverviewTab query={summaryQuery} procedure={procedure} showToast={() => undefined} />
      </section>
    )
  }

  if (showCorrelation) {
    return (
      <section className="output-run-preview" aria-label="只读结果预览">
        <div className="section-heading-row">
          <div>
            <p className="eyebrow">只读结果</p>
            <h3>本次运行结果预览</h3>
          </div>
        </div>
        <EmpiricalCorrelationTab query={correlationQuery} reportOptions={options} />
      </section>
    )
  }

  return (
    <p className="muted">
      该方法的完整只读结果预览仍在迁移中；可通过“打开该运行结果 / 设置”进入现有结果渲染器查看。
    </p>
  )
}
