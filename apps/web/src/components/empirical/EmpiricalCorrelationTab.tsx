import type { EmpiricalAnalysisSegmentMap } from '../../types'
import type { EmpiricalAnalysisOptions } from '../../types'
import type { SegmentQueryState } from './segmentQuery'

import { metric, significance } from './resultFormatters'
import { CorrelationHeatmap } from './CorrelationHeatmap'
import { PaperReadySummaryTable } from './PaperReadySummaryTable'
import { VirtualizedCorrelationTable } from './VirtualizedCorrelationTable'
import { SegmentLoader } from './EmpiricalBadges'
import { DiagnosticAlertCard } from '../shared/DiagnosticAlertCard'

interface EmpiricalCorrelationTabProps {
  query: SegmentQueryState<EmpiricalAnalysisSegmentMap['correlation']>
  reportOptions: Pick<EmpiricalAnalysisOptions, 'correlationMethod'>
}

export function EmpiricalCorrelationTab({ query, reportOptions }: EmpiricalCorrelationTabProps) {
if (query.isLoading) return <SegmentLoader />
if (query.isError) return <div className="error-banner">加载相关矩阵失败: {String(query.error)}</div>
const data = query.data
if (!data?.correlations) return null
return (
  <>
    {data.paperSummaryTable ? (
      <PaperReadySummaryTable
        table={data.paperSummaryTable}
        metric={metric}
        significance={significance}
      />
    ) : null}
    <section className="evidence-section" aria-labelledby="correlation-heading">
      <div className="section-heading"><div><p className="eyebrow">Correlation detail</p><h2 id="correlation-heading">{reportOptions?.correlationMethod === 'spearman' ? 'Spearman 秩相关矩阵' : reportOptions?.correlationMethod === 'partial' ? '偏相关矩阵' : 'Pearson 相关矩阵'}</h2></div></div>
      {data.correlations.inferenceAvailable === false ? (
        <DiagnosticAlertCard
          type="warning"
          title="nested 数据仅显示描述性相关"
          subtitle="逐行独立性推断未执行"
          recommendation="如需 p 值或区间，请使用 cluster-aware 相关推断或多层模型；不得把当前系数的行数当作独立样本量。"
        >
          <p>原因：{data.correlations.inferenceReason}</p>
        </DiagnosticAlertCard>
      ) : null}
      <div className="table-wrap">
        <VirtualizedCorrelationTable
          variables={data.correlations.variables}
          coefficients={data.correlations.coefficients}
          pValues={data.correlations.pValues}
          counts={data.correlations.counts}
          ciLower={data.correlations.ciLower ?? []}
          ciUpper={data.correlations.ciUpper ?? []}
          metric={metric}
          significance={significance}
          confidenceLevel={data.correlations.confidenceLevel}
        />
      </div>
      <p className="method-note">
        {data.correlations.inferenceAvailable === false
          ? '当前仅显示描述性系数与成对观测行数；p 值、显著性星号和普通 Fisher z 区间均未生成。'
          : `星号基于 ${data.correlations.multiplicity?.adjustment ?? '未记录'} 调整 p 值（family=${data.correlations.multiplicity?.familyId ?? '未记录'}，m=${data.correlations.multiplicity?.familySize ?? '—'}）；* p < .05，** p < .01，*** p < .001。原始与调整 p 值均保存在结果和导出中；${Math.round((data.correlations.confidenceLevel ?? 0.95) * 100)}% CI 为单个区间，未作同时校正。${data.correlations.confidenceIntervalMethod ?? ''}`}
      </p>
      <CorrelationHeatmap
        confidenceLevel={data.correlations.confidenceLevel}
        variables={data.correlations.variables}
        coefficients={data.correlations.coefficients}
        pValues={data.correlations.pValues}
        counts={data.correlations.counts}
        ciLower={data.correlations.ciLower ?? []}
        ciUpper={data.correlations.ciUpper ?? []}
      />
    </section>
  </>
)
}
