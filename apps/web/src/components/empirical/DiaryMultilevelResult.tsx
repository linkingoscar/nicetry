import type React from 'react'
import type { DiaryMultilevelResult as DiaryResult } from '../../types'
import { DiaryDataQualityResult } from './DiaryDataQualityResult'
import { DiaryCenteringTrendResult } from './DiaryCenteringTrendResult'
import { DiaryDsemResult } from './DiaryDsemResult'
import { DiaryGlmmEvidenceResult } from './DiaryGlmmEvidenceResult'
import { MethodRobustnessResult } from './MethodRobustnessResult'
import { MonteCarloPowerResult } from './MonteCarloPowerResult'
import { StatTable, type ColumnDef } from '../shared/StatTable'
import { EvidenceSection } from '../shared/EvidenceSection'
import { formatCI, formatMetric, formatPValue } from '../../utils/statFormatters'

interface Props {
  result: DiaryResult
  metric?: (v?: number | null, d?: number) => string
  probability?: (v?: number | null) => string
}

export const DiaryMultilevelResult: React.FC<Props> = ({ result, metric, probability }) => {
  const m = metric || formatMetric
  const p = probability || formatPValue

  type FixedRow = NonNullable<typeof result.fixedEffects>[number]
  type IndirectRow = NonNullable<typeof result.indirectEffects>[number]

  const fixedColumns: ColumnDef<FixedRow>[] = [
    { header: '固定效应', accessor: (r: FixedRow) => r.label, align: 'left' },
    { header: 'B', accessor: (r: FixedRow) => m(r.estimate) },
    { header: 'SE', accessor: (r: FixedRow) => m(r.standardError) },
    { header: 'df', accessor: (r: FixedRow) => m(r.degreesOfFreedom, 1) },
    { header: 't', accessor: (r: FixedRow) => m(r.statistic) },
    { header: '95% CI', accessor: (r: FixedRow) => formatCI(r.lower, r.upper) },
    { header: 'p', accessor: (r: FixedRow) => p(r.pValue) },
  ]

  if (result.analysisType === 'glmm' && result.effectScale) {
    fixedColumns.push({
      header: result.effectScale,
      accessor: (r: FixedRow) => `${m(r.exponentiatedEstimate)} ${formatCI(r.exponentiatedLower, r.exponentiatedUpper)}`,
    })
  }

  if (result.missingData) {
    fixedColumns.push({
      header: 'FMI',
      accessor: (r: FixedRow) => m(r.fractionMissingInformation),
    })
  }

  const indirectColumns: ColumnDef<IndirectRow>[] = [
    {
      header: '效应',
      accessor: (r: IndirectRow) => (r.id === 'indirect_within' ? '个体内间接效应' : '个体间间接效应'),
      align: 'left',
    },
    { header: '估计', accessor: (r: IndirectRow) => m(r.estimate) },
    { header: 'SE', accessor: (r: IndirectRow) => m(r.standardError) },
    { header: '95% CI', accessor: (r: IndirectRow) => formatCI(r.lower, r.upper) },
    { header: 'p', accessor: (r: IndirectRow) => p(r.pValue) },
  ]

  return (
    <div className="space-y-6">
      <DiaryDataQualityResult result={result} metric={m} />
      <DiaryCenteringTrendResult result={result} metric={m} probability={p} />
      <DiaryDsemResult result={result} metric={m} />
      <DiaryGlmmEvidenceResult result={result} metric={m} probability={p} />
      {result.robustnessChecks ? <MethodRobustnessResult diary={result.robustnessChecks} metric={m} /> : null}
      {result.powerAnalysis ? <MonteCarloPowerResult diary={result.powerAnalysis} metric={m} /> : null}

      {(result.analysisType === 'lmm' || result.analysisType === 'glmm') && result.fixedEffects ? (
        <EvidenceSection
          title="固定效应估计"
          methodNote={`中心化：${result.centering}；个体内成分：${result.withinPredictorId ?? '—'}；个体间成分：${result.betweenPredictorId ?? '—'}。`}
        >
          <StatTable columns={fixedColumns} data={result.fixedEffects} rowKey={(row) => row.term} />
        </EvidenceSection>
      ) : null}

      {result.analysisType === 'mediation' && result.indirectEffects ? (
        <EvidenceSection title="分层间接效应" methodNote={result.methodNotice}>
          <StatTable columns={indirectColumns} data={result.indirectEffects} rowKey={(row) => row.id} />
        </EvidenceSection>
      ) : null}
    </div>
  )
}
