import type { EmpiricalAnalysisSegmentMap } from '../../types'
import type { SegmentQueryState } from './segmentQuery'

import { metric, probability } from './resultFormatters'
import { MissingDataReport } from './MissingDataReport'
import { AcademicInterpretation } from '../shared/AcademicInterpretation'
import { APATableExporter } from '../shared/APATableExporter'
import { DiagnosticAlertCard } from '../shared/DiagnosticAlertCard'
import { CopyIcon } from '../shared/Icons'
import { SegmentLoader } from './EmpiricalBadges'
import { ScrollableResultTable } from '../shared/ScrollableResultTable'

interface EmpiricalOverviewTabProps {
  procedure?: import('../../types/empirical-types').EmpiricalProcedure
  query: SegmentQueryState<EmpiricalAnalysisSegmentMap['summary']>
  showToast: (msg: string) => void
}

export function EmpiricalOverviewTab({ query, showToast, procedure }: EmpiricalOverviewTabProps) {
if (query.isLoading) return <SegmentLoader />
if (query.isError) return <div className="error-banner">加载摘要数据失败: {String(query.error)}</div>
const data = query.data
if (!data) return null
const sampleAdequacy = data.sample?.measurementAdequacy
const hasDistributionConcern = data.descriptives?.some(
  (row: { skewness: number | null; kurtosis: number | null }) =>
    (row.skewness !== null && Math.abs(row.skewness) > 2.0)
    || (row.kurtosis !== null && Math.abs(row.kurtosis) > 7.0),
)
const factorabilityLooksUsable =
  typeof data.factorability?.kmo === 'number'
  && data.factorability.kmo >= 0.7
  && typeof data.factorability?.bartlett?.pValue === 'number'
  && data.factorability.bartlett.pValue < 0.05
return (
  <>
    {!procedure && data.academicInterpretation ? (
      <section className="equation-result interpretation-section">
        <details open>
          <summary className="academic-interpretation-summary">
            <span>中文自动解读与 APA 报告规范</span>
          </summary>
          <div className="academic-interpretation-actions">
            <button
              type="button"
              className="academic-interpretation-copy-btn"
              style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              onClick={() => {
                navigator.clipboard.writeText(data.academicInterpretation || '')
                showToast('已复制学术解读文本到剪贴板，可直接粘贴到 Word！')
              }}
            >
              <CopyIcon size={14} /> 复制解读文本
            </button>
            {data.apaTables ? (
              <APATableExporter markdownTable={data.apaTables} title="实证问卷分析 - APA 三线表" />
            ) : null}
          </div>
          <AcademicInterpretation text={data.academicInterpretation} />
        </details>
      </section>
    ) : null}

    {!procedure ? <section className="empirical-summary" aria-label="分析摘要">
      <div><span>总样本</span><strong>{data.sample?.rowCount ?? '—'}</strong></div>
      <div><span>题项完整案例</span><strong>{data.sample?.itemCompleteCases ?? '—'}</strong></div>
      <div><span>KMO</span><strong>{metric(data.factorability?.kmo)}</strong></div>
      <div><span>Harman 首因子</span><strong>{metric(data.commonMethodBias?.firstFactorVariancePercent, 1)}%</strong></div>
      <div>
        <span>CFA</span>
        <strong>
          {data.cfa?.available
            ? data.cfa.validForConfirmatoryInterpretation === false
              ? '可计算 · 解释受限'
              : '可用'
            : '不可用'}
        </strong>
      </div>
      <div><span>EFA</span><strong>{data.efa?.factorCount ?? '—'} 因子</strong></div>
    </section> : null}

    <section className="evidence-section" aria-labelledby="sample-flow-heading">
      <div className="section-heading"><div><p className="eyebrow">Analysis provenance</p><h2 id="sample-flow-heading">样本流与发布边界</h2></div></div>
      <p className="method-note">
        原始 {data.sampleFlow?.original ?? data.sample?.rowCount ?? '—'} → 纳入 {data.sampleFlow?.included ?? data.sample?.rowCount ?? '—'} → 最终 N {data.sampleFlow?.finalN ?? data.sampleFlow?.included ?? data.sample?.rowCount ?? '—'}；缺失策略：{data.sampleFlow?.missingMethod ?? '分段 complete/pairwise'}。
      </p>
      {data.requiresManualReview || data.publicationEligible === false ? (
        <div className="error-banner" role="status">当前结果需要人工复核，不能直接作为论文主分析发布：{data.publicationEligibilityReasons?.join('、') ?? '存在方法边界或数值回退。'}</div>
      ) : <p className="method-note">当前未触发已登记的发布阻断条件；仍需结合研究计划、估计对象与诊断逐项复核。</p>}
    </section>

    {data.commonMethodBias?.firstFactorVariancePercent && data.commonMethodBias.firstFactorVariancePercent > 40 ? (
      <DiagnosticAlertCard
        type="warning"
        title="Harman 单因子共同方法偏差 (CMB) 预警"
        subtitle="建议复核控制"
        recommendation="建议在论文中补充未测量潜在共同因子 (ULMC) 或标记多时点/多来源测量控制方案。"
      >
        首因子解释方差为 <strong>{metric(data.commonMethodBias.firstFactorVariancePercent, 1)}%</strong>（超过学术常规临界值 40%），提示可能存在共同方法偏差风险。
      </DiagnosticAlertCard>
    ) : null}

    {sampleAdequacy?.status === 'caution' ? (
      <DiagnosticAlertCard
        type="warning"
        title="样本信息不足以支持稳定的确认性测量结论"
        subtitle="可计算不等于可确认"
        recommendation="将当前 EFA/CFA 视为探索或流程演示；正式研究应结合预期效应、模型复杂度、估计量与缺失机制进行前瞻性样本量规划，并在更充分样本中交叉验证。"
      >
        题项完整案例 <strong>N = {sampleAdequacy.completeCases}</strong>，估计自由参数约{' '}
        <strong>{sampleAdequacy.estimatedParameterCount}</strong>，每自由参数案例数{' '}
        <strong>{metric(sampleAdequacy.casesPerParameter, 2)}</strong>。平台采用透明的保守护栏
        （N ≥ {sampleAdequacy.minimumCompleteCasesGuardrail} 且每自由参数案例数 ≥{' '}
        {sampleAdequacy.minimumCasesPerParameterGuardrail}）；这不是通用样本量定理。
      </DiagnosticAlertCard>
    ) : hasDistributionConcern ? (
      <DiagnosticAlertCard
        type="important"
        title="正态性分布偏度/峰度诊断提醒"
        subtitle="正态分布检验"
        recommendation="对偏态较大的变量，建议在后续 PROCESS 回归分析中勾选 Bootstrap 5,000 次非参数抽样或进行对数变换。"
      >
        检测到部分题项/变量偏度 |Skew| &gt; 2.0 或峰度 |Kurt| &gt; 7.0；请结合图形、估计量与稳健标准误进一步判断分布影响。
      </DiagnosticAlertCard>
    ) : factorabilityLooksUsable ? (
      <DiagnosticAlertCard
        type="good"
        title="因子分析前置诊断未见明显阻断信号"
        subtitle="仍需结合样本与模型诊断"
      >
        KMO = {metric(data.factorability?.kmo)}，且 Bartlett 球形检验达到统计显著；这仅支持相关矩阵具有可因子化信号，不等同于模型正确或样本充分。
      </DiagnosticAlertCard>
    ) : !procedure ? (
      <DiagnosticAlertCard
        type="warning"
        title="因子分析前置诊断需要复核"
        subtitle="暂不作适合性结论"
      >
        当前 KMO 或 Bartlett 诊断未同时满足常用参考条件。请检查题项相关结构、样本构成和数据质量后再解释因子结果。
      </DiagnosticAlertCard>
    ) : null}

    {data.descriptives?.length ? <section className="evidence-section" aria-labelledby="descriptive-heading">
      <div className="section-heading"><div><p className="eyebrow">Table 1</p><h2 id="descriptive-heading">描述统计与分布诊断</h2></div></div>
      <ScrollableResultTable label="描述统计表（可横向滚动）">
        <table className="result-table empirical-table">
          <thead><tr><th>变量</th><th>N</th><th>缺失</th><th>M</th><th>SD</th><th>范围</th><th>偏度</th><th>峰度</th><th>|z| &gt; 3.29</th></tr></thead>
          <tbody>{data.descriptives?.map((row: { id: string; label: string; n: number; missing: number; mean: number | null; sd: number | null; minimum: number | null; maximum: number | null; skewness: number | null; kurtosis: number | null; outlierCount: number }) => (
            <tr key={row.id}><th>{row.label}</th><td>{row.n}</td><td>{row.missing}</td><td>{metric(row.mean)}</td><td>{metric(row.sd)}</td><td>{metric(row.minimum)}–{metric(row.maximum)}</td><td>{metric(row.skewness)}</td><td>{metric(row.kurtosis)}</td><td>{row.outlierCount}</td></tr>
          ))}</tbody>
        </table>
      </ScrollableResultTable>
    </section> : null}
    {data.missingDataReport ? <MissingDataReport report={data.missingDataReport} metric={metric} probability={probability} /> : null}

    {data.frequencies?.length ? (
      <section className="evidence-section" aria-labelledby="frequency-heading">
        <div className="section-heading"><div><p className="eyebrow">Sample profile</p><h2 id="frequency-heading">人口统计与分类变量频数</h2></div></div>
        <div className="frequency-grid">{data.frequencies.map((row: { id: string; label: string; levels: Array<{ level: string; count: number; proportion: number }> }) => (
          <article key={row.id}><strong>{row.label}</strong>{row.levels.map((level: { level: string; count: number; proportion: number }) => (
            <div key={level.level}><span>{level.level}</span><span>{level.count}（{(level.proportion * 100).toFixed(1)}%）</span></div>
          ))}</article>
        ))}</div>
      </section>
    ) : null}
  </>
)
}
