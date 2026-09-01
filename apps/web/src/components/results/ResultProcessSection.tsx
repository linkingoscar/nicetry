import { ScrollableResultTable } from '../shared/ScrollableResultTable'
import type { ResultBundle } from '../../types'
import { APATableExporter } from '../shared/APATableExporter'
import { JohnsonNeymanPlot } from './JohnsonNeymanPlot'
import { SimpleSlopePlot } from './SimpleSlopePlot'

interface ResultProcessSectionProps {
  result: ResultBundle
  title: string
}

function formatNumber(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

export function ResultProcessSection({ result, title }: ResultProcessSectionProps) {
  const effects = Object.fromEntries(result.effects.map((effect) => [effect.label, effect]) ?? [])
  const indirect = effects.a_x_b

  return (
    <>
      {result.claimBoundary?.claimMode === 'association' ? (
        <div className="method-note" role="note">本模型结果按 association / 关联性证据解释；横截面数据不生成时间顺序、机制或因果效应措辞。</div>
      ) : null}
      {result.requiresManualReview ? (
        <div className="error-banner" role="status">当前结果需要人工复核：{result.publicationEligibilityReasons?.join('、') ?? '存在稳健标准误或 Bootstrap 回退。'}</div>
      ) : null}
      {indirect ? (
        <div className="stat-grid" aria-live="polite">
          <div className="stat">
            <span>路径 a</span>
            <strong>{formatNumber(effects.a?.estimate)}</strong>
          </div>
          <div className="stat">
            <span>路径 b</span>
            <strong>{formatNumber(effects.b?.estimate)}</strong>
          </div>
          <div className="stat">
            <span>直接效应 c′</span>
            <strong>{formatNumber(effects.c_prime?.estimate)}</strong>
          </div>
          <div className="stat stat-accent">
            <span>间接效应 a×b</span>
            <strong>{formatNumber(indirect?.estimate)}</strong>
          </div>
        </div>
      ) : null}

      <ScrollableResultTable className="effect-table-wrap" label="效应汇总表">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', flexWrap: 'wrap', gap: '8px' }}>
          <span className="eyebrow" style={{ margin: 0 }}>效应汇总表</span>
          <APATableExporter
            title={`${title} - 效应估计表`}
            data={{
              title: `${title} - 效应汇总`,
              headers: ['效应', '类型', '估计值', '95% 置信区间'],
              rows: result.effects.map((e) => [
                e.label,
                e.type,
                formatNumber(e.estimate),
                e.confidenceInterval ? `[${formatNumber(e.confidenceInterval.lower)}, ${formatNumber(e.confidenceInterval.upper)}]` : '—'
              ])
            }}
          />
        </div>
        <table className="result-table">
          <thead><tr><th>效应</th><th>类型</th><th>估计</th><th>区间</th></tr></thead>
          <tbody>
            {result.effects.map((effect) => (
              <tr key={effect.id}>
                <th scope="row">{effect.label}</th>
                <td>{effect.type}</td>
                <td>{formatNumber(effect.estimate)}</td>
                <td>{effect.confidenceInterval ? `[${formatNumber(effect.confidenceInterval.lower)}, ${formatNumber(effect.confidenceInterval.upper)}]` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </ScrollableResultTable>

      {indirect?.confidenceInterval ? (
        <div className="interval-block">
          <span>95% bootstrap CI</span>
          <strong>
            [{formatNumber(indirect.confidenceInterval.lower)}, {' '}
            {formatNumber(indirect.confidenceInterval.upper)}]
          </strong>
        </div>
      ) : null}

      <dl className="run-meta">
        <div><dt>分析样本</dt><dd>{result.sampleFlow.included}</dd></div>
        <div><dt>运行 ID</dt><dd>{result.run.id.slice(0, 16)}…</dd></div>
        <div><dt>统计引擎</dt><dd>{result.provenance.engineVersion}</dd></div>
        <div><dt>标准误</dt><dd>{result.provenance.standardErrors?.toUpperCase() ?? 'classical'}</dd></div>
        <div><dt>Bootstrap 家族</dt><dd>{result.bootstrap ? `${result.bootstrap.familyId} · 有效 ${result.bootstrap.replicatesValid}/${result.bootstrap.replicatesRequested}` : '—'}</dd></div>
        <div><dt>耗时</dt><dd>{result.run.durationMilliseconds ?? 0} ms</dd></div>
      </dl>

      {result.equations.map((equation) => {
        const isWaldZ = equation.modelFamily === 'binomial_logit' || equation.coefficients?.some((c) => c.confidenceInterval?.method === 'wald_z')
        const isMcFadden = equation.rSquaredType === 'mcfadden_pseudo_r_squared' || isWaldZ
        return (
          <section className="equation-result" key={equation.id}>
            <strong>
              {equation.outcomeRole.toUpperCase()} 方程 · {isMcFadden ? `McFadden R² ${equation.rSquared.toFixed(3)}${equation.nagelkerkeRSquared !== undefined && equation.nagelkerkeRSquared !== null ? `，Nagelkerke R² ${equation.nagelkerkeRSquared.toFixed(3)}` : ''}` : `R² ${equation.rSquared.toFixed(3)} (调整后 R² ${equation.adjustedRSquared.toFixed(3)})`}
            </strong>
            <code>{equation.formula}</code>
            <ScrollableResultTable className="effect-table-wrap" label={`${equation.outcomeRole.toUpperCase()} 方程系数表`}>
              <table className="result-table">
                <thead>
                  <tr>
                    <th>项</th>
                    <th>B</th>
                    <th>SE</th>
                    <th>{isWaldZ ? 'z' : 't'}</th>
                    <th>p</th>
                    {isWaldZ ? <th>OR（95% CI）</th> : null}
                    {isWaldZ ? <th>AME（区间）</th> : null}
                  </tr>
                </thead>
                <tbody>
                  {equation.coefficients?.map((coefficient) => (
                    <tr key={coefficient.term}>
                      <th scope="row">{coefficient.term}</th>
                      <td>{formatNumber(coefficient.estimate)}</td>
                      <td>{formatNumber(coefficient.standardError)}</td>
                      <td>{formatNumber(coefficient.statistic)}</td>
                      <td>{coefficient.pValue < 0.001 ? '< .001' : coefficient.pValue.toFixed(3)}</td>
                      {isWaldZ ? (
                        <td>
                          {typeof coefficient.oddsRatio === 'number'
                            ? `${formatNumber(coefficient.oddsRatio)} [${formatNumber(coefficient.oddsRatioConfidenceInterval?.lower)}, ${formatNumber(coefficient.oddsRatioConfidenceInterval?.upper)}]`
                            : '—'}
                        </td>
                      ) : null}
                      {isWaldZ ? (
                        <td>
                          {coefficient.marginalEffectType === 'not_applicable_interaction_term'
                            ? <span title={coefficient.marginalEffectReason}>不适用：查看条件效应</span>
                            : typeof coefficient.averageMarginalEffect === 'number'
                            ? `${formatNumber(coefficient.averageMarginalEffect)} [${formatNumber(coefficient.marginalEffectConfidenceInterval?.lower)}, ${formatNumber(coefficient.marginalEffectConfidenceInterval?.upper)}]`
                            : '—'}
                        </td>
                      ) : null}
                    </tr>
                  ))}
                </tbody>
              </table>
            </ScrollableResultTable>
          </section>
        )
      })}

      {result.probes && result.probes.length > 0 ? (
        <section className="equation-result">
          <strong>简单斜率</strong>
          <ScrollableResultTable className="effect-table-wrap" label="简单斜率表">
            <table className="result-table">
              <thead><tr><th>路径</th><th>条件</th><th>W</th>{result.probes.some((probe) => probe.secondaryModeratorValue !== undefined) ? <th>Z</th> : null}<th>效应</th><th>SE</th><th>t/z</th><th>p</th><th>95% CI</th><th>SE/CI 方法</th></tr></thead>
              <tbody>{result.probes.map((probe) => (
                <tr key={probe.label}>
                  <td>{probe.predictorLabel ?? probe.targetEdgeId ?? '—'}</td>
                  <th scope="row">{probe.label}</th>
                  <td>{formatNumber(probe.moderatorValue)}</td>
                  {result.probes?.some((item) => item.secondaryModeratorValue !== undefined) ? <td>{probe.secondaryModeratorValue === undefined ? '—' : formatNumber(probe.secondaryModeratorValue)}</td> : null}
                  <td>{formatNumber(probe.effect)}</td>
                  <td>{formatNumber(probe.standardError)}</td>
                  <td>{formatNumber(probe.statistic)}</td>
                  <td>{probe.pValue < 0.001 ? '< .001' : probe.pValue.toFixed(3)}</td>
                  <td>[{formatNumber(probe.confidenceInterval.lower)}, {formatNumber(probe.confidenceInterval.upper)}]</td>
                  <td>{probe.confidenceInterval.method}</td>
                </tr>
              ))}</tbody>
            </table>
          </ScrollableResultTable>
          {result.moderationPlots?.map((plot) => (
            <SimpleSlopePlot key={plot.id} plot={plot} />
          ))}
          {result.johnsonNeymanResults?.map((item) => (
            <JohnsonNeymanPlot key={item.moderationId} predictorLabel={item.predictorLabel} moderatorLabel={item.moderatorLabel} result={item.result} />
          ))}
          {!result.johnsonNeymanResults?.length && result.johnsonNeyman ? (
            result.johnsonNeyman.available
              ? <p className="method-note">Johnson–Neyman 临界点：{formatNumber(result.johnsonNeyman.lower)}、{formatNumber(result.johnsonNeyman.upper)}；观测范围 [{formatNumber(result.johnsonNeyman.observedMinimum)}, {formatNumber(result.johnsonNeyman.observedMaximum)}]。</p>
              : <p className="method-note">观测范围内未得到两个有限 Johnson–Neyman 临界点。</p>
          ) : null}
        </section>
      ) : null}

      {result.diagnostics && result.diagnostics.length > 0 ? (
        <section className="equation-result">
          <strong>回归诊断</strong>
          <ScrollableResultTable className="effect-table-wrap" label="回归诊断表">
            <table className="result-table">
              <thead><tr><th>方程</th><th>残差 SE</th><th>最大杠杆</th><th>最大 Cook D</th><th>BP p</th></tr></thead>
              <tbody>{result.diagnostics.map((diagnostic) => (
                <tr key={diagnostic.equationId}>
                  <th scope="row">{diagnostic.equationId}</th>
                  <td>{formatNumber(diagnostic.residualStandardError)}</td>
                  <td>{formatNumber(diagnostic.maximumLeverage)}</td>
                  <td>{formatNumber(diagnostic.maximumCooksDistance)}</td>
                  <td>{diagnostic.heteroskedasticity.pValue < 0.001 ? '< .001' : diagnostic.heteroskedasticity.pValue.toFixed(3)}</td>
                </tr>
              ))}</tbody>
            </table>
          </ScrollableResultTable>
          <p className="method-note">诊断用于识别异方差与影响点，不作为机械删样本规则。</p>
        </section>
      ) : null}
    </>
  )
}
