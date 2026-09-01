import type { EmpiricalAnalysisSegmentMap } from '../../types'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'
import type { SegmentQueryState } from './segmentQuery'

import { metric, probability } from './resultFormatters'
import { RegressionRobustnessTable } from './RegressionRobustnessTable'
import { RelativeImportanceTable } from './RelativeImportanceTable'
import { ResponseSurfaceAnalysis } from './ResponseSurfaceAnalysis'
import { renderSigBadge, SegmentLoader, VisualCIBar } from './EmpiricalBadges'

interface EmpiricalRegressionTabProps {
  query: SegmentQueryState<EmpiricalAnalysisSegmentMap['regression']>
  activeTab: EmpiricalResultTab
}

export function EmpiricalRegressionTab({ query, activeTab }: EmpiricalRegressionTabProps) {
if (query.isLoading) return <SegmentLoader />
if (query.isError) return <div className="error-banner">加载差异与回归数据失败: {String(query.error)}</div>
const data = query.data
if (!data) return null
const gc = data.groupComparison?.results?.length ? data.groupComparison : null
const groupConfidencePercent = gc
  ? Math.round((gc.results[0]?.confidenceLevel ?? 0.95) * 100)
  : 95
const aggregation = data.aggregationDiagnostics?.constructs?.length
  ? data.aggregationDiagnostics
  : null
const reg = data.hierarchicalRegression?.blocks?.length
  ? data.hierarchicalRegression
  : null
const responseSurface = data.responseSurface?.available !== undefined
  ? data.responseSurface
  : null
return (
  <>
    {activeTab === 'groups' && aggregation ? (
      <section className="evidence-section" aria-labelledby="aggregation-heading">
        <div className="section-heading"><div><p className="eyebrow">Cluster aggregation diagnostics</p><h2 id="aggregation-heading">按“{aggregation.groupLabel}”的聚合诊断</h2></div></div>
        <p className="method-note">{aggregation.guidance}</p>
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead><tr><th>构念</th><th>cluster 数</th><th>规模范围</th><th>有效平均规模</th><th>ICC(1)</th><th>ICC(2)</th><th>设计效应</th><th>平均 rwg(j)</th><th>中位 rwg(j)</th></tr></thead>
            <tbody>{aggregation.constructs.map((row) => (
              <tr key={row.id}>
                <th>{row.label}</th>
                {row.available ? (
                  <>
                    <td>{row.clusterCount}</td><td>{row.minimumClusterSize}–{row.maximumClusterSize}</td><td>{metric(row.averageClusterSize)}</td><td>{metric(row.icc1)}</td><td>{metric(row.icc2)}</td><td>{metric(row.designEffect)}</td><td>{metric(row.rwg?.mean)}</td><td>{metric(row.rwg?.median)}</td>
                  </>
                ) : <td colSpan={8}>{row.reason ?? '当前数据不足以计算聚合诊断。'}</td>}
              </tr>
            ))}</tbody>
          </table>
        </div>
        <p className="method-note">rwg(j) 使用矩形随机响应零分布，并按题项数及均值/求和计分方式缩放期望方差；负值保留为组内变异超过零分布的诊断信号。</p>
      </section>
    ) : null}
    {activeTab === 'groups' && gc ? (
      <section className="evidence-section" aria-labelledby="group-heading">
        <div className="section-heading"><div><p className="eyebrow">Difference tests</p><h2 id="group-heading">按“{gc.groupLabel}”的组间差异</h2></div></div>
        <p className="method-note">主模型策略：{gc.analysisPolicy?.primaryModel ?? '预先声明的组间主模型'}；{gc.analysisPolicy?.selectionRule ?? '不根据 p 值自动切换。'} Brown–Forsythe 仅作 {gc.analysisPolicy?.brownForsytheRole ?? 'diagnostic_only'}，Welch 结果只作敏感性分析。跨构念 omnibus 使用 {gc.multiplicity?.adjustment ?? '未记录'} 校正（family={gc.multiplicity?.globalFamilyId ?? gc.multiplicity?.primaryFamilyId ?? '未记录'}）；原始与调整后 p 均随结果和导出保存。</p>
        <div className="table-wrap"><table className="result-table empirical-table"><thead><tr><th>构念</th><th>检验</th><th>统计量</th><th>p</th><th>效应量</th><th>{groupConfidencePercent}% CI / ω²</th><th>各组 M (SD)</th></tr></thead><tbody>{gc.results.map((row) => row.unavailable ? <tr key={row.id}><th>{row.label}</th><td colSpan={6}><span className="validation-error">{row.reason ?? '组间比较因样本不足被跳过。'}</span></td></tr> : <tr key={row.id}><th>{row.label}</th><td>{row.test}</td><td>{metric(row.statistic)}</td><td>{probability(row.pValue)}</td><td>{metric(row.effectSize)} {row.effectSizeType}</td><td>{row.effectSizeCiLower != null && row.effectSizeCiUpper != null ? `[${metric(row.effectSizeCiLower)}, ${metric(row.effectSizeCiUpper)}]` : row.omegaSquared != null ? `ω² = ${metric(row.omegaSquared)}` : '—'}</td><td>{row.groups.map((group) => `${group.level}: ${metric(group.mean)} (${metric(group.sd)})`).join('；')}</td></tr>)}</tbody></table></div>
        <p className="method-note">两组比较给出小样本校正 Hedges g 的近似 {Math.round((gc.results[0]?.effectSizeConfidenceLevel ?? 0.95) * 100)}% CI；多组比较同时给出 η² 与偏差校正的 ω²。效应量不按固定阈值自动定性。</p>
        {gc.results.some((row) => row.robustTest) ? (
          <div className="table-wrap" style={{ marginTop: '1.5rem' }}>
            <strong>方差稳健性诊断与 Welch ANOVA</strong>
            <table className="result-table empirical-table">
              <thead><tr><th>构念</th><th>Brown–Forsythe p</th><th>稳健检验</th><th>统计量</th><th>df1</th><th>df2</th><th>p</th></tr></thead>
              <tbody>{gc.results.filter((row) => row.robustTest).map((row) => (
                <tr key={`${row.id}-robust`}>
                  <th scope="row">{row.label}</th><td>{probability(row.assumptionTests?.brownForsythe.pValue ?? null)}</td><td>{row.robustTest?.method}</td><td>{metric(row.robustTest?.statistic ?? null)}</td><td>{metric(row.robustTest?.df1 ?? null)}</td><td>{metric(row.robustTest?.df2 ?? null)}</td><td>{probability(row.robustTest?.pValue ?? null)}</td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : null}
        {gc.results.some((row) => row.pairwiseTukey && row.pairwiseTukey.length > 0) ? (
          <div className="table-wrap" style={{ marginTop: '1.5rem' }}>
            <strong>事后多重比较 (ANOVA Post-Hoc Pairwise Comparisons)</strong>
            <table className="result-table empirical-table">
              <thead><tr><th>构念</th><th>对比组</th><th>均值差</th><th>{Math.round((gc.results[0]?.pairwiseTukey?.[0]?.confidenceLevel ?? 0.95) * 100)}% CI</th><th>Tukey adj. p</th><th>Bonferroni adj. p</th><th>Games–Howell p</th></tr></thead>
              <tbody>{gc.results.flatMap((row) => {
                const tukeyItems = row.pairwiseTukey ?? []
                return tukeyItems.map((tItem, idx) => {
                  const reversed = tItem.comparison.split('-').reverse().join('-')
                  const bItem = row.pairwiseBonferroni?.find((item) => item.comparison === tItem.comparison || item.comparison === reversed)
                  const ghItem = row.pairwiseGamesHowell?.find((item) => item.comparison === tItem.comparison || item.comparison === reversed)
                  return (
                    <tr key={`${row.id}-${tItem.comparison}`}>
                      {idx === 0 ? <th scope="row" rowSpan={tukeyItems.length}>{row.label}</th> : null}
                      <td>{tItem.comparison}</td><td>{metric(tItem.difference)}</td><td>[{metric(tItem.lower)}, {metric(tItem.upper)}]</td><td>{probability(tItem.pValue)}</td><td>{bItem ? probability(bItem.pValue) : '—'}</td><td>{ghItem ? probability(ghItem.pValue) : '—'}</td>
                    </tr>
                  )
                })
              })}</tbody>
            </table>
          </div>
        ) : null}
      </section>
    ) : null}

    {activeTab === 'groups' && !aggregation && !gc ? (
      <div className="empty-analysis-state">
        <strong>本次未配置分组变量</strong>
        <p>展开上方“分析设置”，在基础设置中选择分组变量后重新运行，即可生成组间差异、聚合诊断与测量不变性结果。</p>
      </div>
    ) : null}

    {activeTab === 'regression' && reg ? (
      <section className="evidence-section" aria-labelledby="regression-heading">
        <div className="section-heading"><div><p className="eyebrow">Hierarchical OLS</p><h2 id="regression-heading">分层回归：{reg.outcomeLabel}</h2></div></div>
        <p className="method-note">估计对象：{reg.estimand ?? '调整后的均值关联'}；主分析：{reg.primaryAnalysis?.method ?? 'ordinary OLS'}（{reg.primaryAnalysis?.selectionRule ?? '不根据 p 值自动切换'}）。HC3 仅为敏感性分析。</p>
        {reg.underdetermined ? (
          <div className="error-banner" role="alert">
            该区块完整案例数少于或等于待估参数，R²/ΔR² 等统计量无解释价值；系数仅供诊断，不应进入报告。
          </div>
        ) : (
          <p className="method-note">ΔR²={metric(reg.change?.deltaRSquared)}，F-change={metric(reg.change?.statistic)}，p={probability(reg.change?.pValue)}，N={reg.n}。</p>
        )}
        {reg.blocks?.map((block) => (
          <article className="regression-block" key={block.block}>
            <div><strong>区块 {block.block}</strong><span>R²={metric(block.rSquared)} · 调整 R²={metric(block.adjustedRSquared)}</span></div>
            <code>{block.formula}</code>
            <div className="table-wrap">
              <table className="result-table empirical-table">
                <thead><tr><th>变量</th><th>B</th><th>SE</th><th>β (标准化)</th><th>t</th><th>p</th><th>CI</th><th>VIF</th><th>f²</th></tr></thead>
                <tbody>{block.coefficients?.map((row) => (
                  <tr key={row.term}>
                    <th>{row.label}</th><td>{metric(row.estimate)}</td><td>{metric(row.standardError)}</td><td>{row.standardizedEstimate !== undefined ? metric(row.standardizedEstimate) : '—'}</td><td>{metric(row.statistic)}</td><td>{probability(row.pValue)} {renderSigBadge(row.pValue)}</td><td><VisualCIBar lower={row.lower} upper={row.upper} confidenceLevel={reg.primaryAnalysis?.confidenceLevel} /></td><td>{metric(row.vif)}</td><td>{row.cohenF2 !== undefined ? metric(row.cohenF2) : '—'}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          </article>
        ))}
        {reg.robustness ? (
          <RegressionRobustnessTable robustness={reg.robustness} metric={metric} probability={probability} />
        ) : null}
      </section>
    ) : null}
    {activeTab === 'regression' && !reg ? (
      <div className="empty-analysis-state">
        <strong>本次未生成分层回归</strong>
        <p>请在“回归与高级分析”中设置结果变量和预测变量后重新运行。</p>
      </div>
    ) : null}

    {activeTab === 'advanced' && reg?.relativeImportance ? (
      <RelativeImportanceTable result={reg.relativeImportance} metric={metric} />
    ) : null}
    {activeTab === 'advanced' && responseSurface ? (
      <ResponseSurfaceAnalysis result={responseSurface} metric={metric} probability={probability} />
    ) : null}
    {activeTab === 'advanced' && !reg?.relativeImportance && !responseSurface ? (
      <div className="empty-analysis-state">
        <strong>本次未配置高级分析</strong>
        <p>响应面分析需选择两个预测变量；相对重要性分析会随含多个预测变量的回归一并生成。</p>
      </div>
    ) : null}
  </>
)
}
