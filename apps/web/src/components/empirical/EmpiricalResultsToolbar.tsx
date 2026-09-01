import { useState } from 'react'
import { empiricalAnalysisExportUrl } from '../../api'
import { downloadWithSession } from '../../api/client'
import type { EmpiricalAnalysisSegmentMap } from '../../types'
import { openAPAManuscriptReport } from '../../utils/generateFullAPAReport'

interface EmpiricalResultsToolbarProps {
  procedure?: import('../../types/empirical-types').EmpiricalProcedure | null
  datasetId: string
  datasetName: string
  measurementVersion: number | null
  reportId: string
  summary?: EmpiricalAnalysisSegmentMap['summary']
  correlation?: EmpiricalAnalysisSegmentMap['correlation']
}

export function EmpiricalResultsToolbar({
  procedure,
  datasetId,
  datasetName,
  measurementVersion,
  reportId,
  summary,
  correlation,
}: EmpiricalResultsToolbarProps) {
  const [exporting, setExporting] = useState(false)
  const handleExportExcel = async () => {
    setExporting(true)
    try {
      await downloadWithSession(
        empiricalAnalysisExportUrl(datasetId, measurementVersion, reportId),
        `实证分析论文表格-${reportId}.xlsx`,
      )
    } finally {
      setExporting(false)
    }
  }
  return (
    <div className="empirical-results-toolbar">
      {!procedure ? <button
        type="button"
        className="run-button"
        style={{ background: '#0f172a', color: '#ffffff', border: 0 }}
        onClick={() => openAPAManuscriptReport({
          title: '问卷中介效应与实证分析全套报告',
          reportId,
          datasetName,
          sampleCount: summary?.sample?.rowCount,
          kmo: summary?.factorability?.kmo,
          harmanFirstFactor: summary?.commonMethodBias?.firstFactorVariancePercent,
          descriptives: summary?.descriptives,
          correlationTable: correlation?.correlations,
          academicInterpretation: summary?.academicInterpretation,
        })}
      >
        导出完整实证研究报告（APA 手稿）
      </button> : null}
      <button
        type="button"
        className="run-button"
        disabled={exporting}
        onClick={handleExportExcel}
      >
        {exporting ? '正在导出…' : '导出论文表格 Excel'}
      </button>
      <code>报告 ID: {reportId}</code>
    </div>
  )
}
