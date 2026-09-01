import type { LongitudinalPanelResult as LongitudinalPanelResultData } from '../../types'
import { LongitudinalInvarianceResult } from './LongitudinalInvarianceResult'
import { LongitudinalGrowthResult } from './LongitudinalGrowthResult'
import { LongitudinalCmbResult } from './LongitudinalCmbResult'
import { MethodRobustnessResult } from './MethodRobustnessResult'
import { MonteCarloPowerResult } from './MonteCarloPowerResult'

interface LongitudinalPanelResultProps {
  result: LongitudinalPanelResultData | null | undefined
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function LongitudinalPanelResult({
  result,
  metric,
  probability,
}: LongitudinalPanelResultProps) {
  if (!result) {
    return (
      <section className="evidence-section empty-result-state">
        <h2>纵向面板分析</h2>
        <p>本次报告未配置观测得分或题项级潜变量 CLPM、RI-CLPM 或 LCM-SR。</p>
      </section>
    )
  }
  const crossLagged = result.paths.filter((path) => path.pathType === 'cross_lagged')
  const autoregressive = result.paths.filter((path) => path.pathType === 'autoregressive')

  return (
    <section className="evidence-section" aria-labelledby="longitudinal-result-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Longitudinal panel</p>
          <h2 id="longitudinal-result-heading">{result.modelLabel} 交叉滞后结果</h2>
        </div>
        <span className={`status-chip ${result.validForInterpretation ? '' : 'is-warning'}`}>
          {result.validForInterpretation ? '后估计检查通过' : '仅供诊断'}
        </span>
      </div>
      <p className="method-note">{result.causalNotice}</p>
      <dl className="run-meta factor-meta">
        <div><dt>样本</dt><dd>{result.sampleSize}</dd></div>
        <div><dt>波次</dt><dd>{result.waveCount}</dd></div>
        <div><dt>估计</dt><dd>{result.estimator}</dd></div>
        <div><dt>缺失处理</dt><dd>{result.missingMethod}</dd></div>
        <div>
          <dt>测量模式</dt>
          <dd>{result.measurementMode === 'latent_items' ? '题项级潜变量' : '观测得分'}</dd>
        </div>
        <div><dt>CFI</dt><dd>{metric(result.fitIndices.cfi)}</dd></div>
        <div><dt>TLI</dt><dd>{metric(result.fitIndices.tli)}</dd></div>
        <div><dt>RMSEA</dt><dd>{metric(result.fitIndices.rmsea)}</dd></div>
        <div><dt>SRMR</dt><dd>{metric(result.fitIndices.srmr)}</dd></div>
      </dl>
      {result.diagnostics.length ? (
        <div className="diagnostic-list" role="alert">
          {result.diagnostics.map((diagnostic) => (
            <p key={`${diagnostic.code}-${diagnostic.message}`}>{diagnostic.message}</p>
          ))}
        </div>
      ) : null}
      <LongitudinalInvarianceResult
        result={result}
        metric={metric}
        probability={probability}
      />
      <LongitudinalGrowthResult result={result} metric={metric} probability={probability} />
      <LongitudinalCmbResult result={result} metric={metric} probability={probability} />
      <MethodRobustnessResult longitudinal={result.robustnessChecks} metric={metric} />
      <MonteCarloPowerResult longitudinal={result.powerAnalysis} metric={metric} />
      <div className="longitudinal-result-grid">
        <div>
          <h3>交叉滞后路径</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>方向</th><th>时段</th><th>B</th><th>β</th><th>SE</th><th>95% CI</th><th>p</th></tr>
              </thead>
              <tbody>
                {crossLagged.map((path) => (
                  <tr key={path.id}>
                    <th>{path.direction}</th>
                    <td>T{path.fromWave}→T{path.toWave}</td>
                    <td>{metric(path.estimate)}</td>
                    <td>{metric(path.standardizedEstimate)}</td>
                    <td>{metric(path.standardError)}</td>
                    <td>[{metric(path.lower)}, {metric(path.upper)}]</td>
                    <td>{probability(path.pValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div>
          <h3>自回归路径</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead><tr><th>方向</th><th>时段</th><th>B</th><th>β</th><th>p</th></tr></thead>
              <tbody>
                {autoregressive.map((path) => (
                  <tr key={path.id}>
                    <th>{path.direction}</th>
                    <td>T{path.fromWave}→T{path.toWave}</td>
                    <td>{metric(path.estimate)}</td>
                    <td>{metric(path.standardizedEstimate)}</td>
                    <td>{probability(path.pValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <h3>逐波样本流</h3>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead><tr><th>波次</th><th>时间值</th><th>有效</th><th>上期保留</th><th>流失</th><th>重新进入</th></tr></thead>
          <tbody>
            {result.waveSampleFlow.map((wave) => (
              <tr key={wave.label}>
                <th>{wave.label}</th><td>{wave.timeValue}</td><td>{wave.observed}</td>
                <td>{wave.retainedFromPrevious}</td><td>{wave.attritionFromPrevious}</td>
                <td>{wave.reenteredFromPrevious}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
