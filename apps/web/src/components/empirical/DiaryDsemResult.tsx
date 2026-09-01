import type { DiaryMultilevelResult } from '../../types'
import { DiaryDsemPlots } from './DiaryDsemPlots'

interface DiaryDsemResultProps {
  result: DiaryMultilevelResult
  metric: (value: number | null | undefined, digits?: number) => string
}

export function DiaryDsemResult({ result, metric }: DiaryDsemResultProps) {
  if (result.analysisType !== 'bayesian_dsem' || !result.mcmcDiagnostics) return null
  const diagnostics = result.mcmcDiagnostics
  return (
    <section className="analysis-result-subsection" aria-labelledby="dsem-result-heading">
      <h3 id="dsem-result-heading">动态路径后验</h3>
      <dl className="run-meta factor-meta">
        <div><dt>链数</dt><dd>{diagnostics.chains}</dd></div>
        <div><dt>每链保留</dt><dd>{diagnostics.retainedPerChain}</dd></div>
        <div><dt>最大 R-hat</dt><dd>{metric(diagnostics.maximumRHat)}</dd></div>
        <div><dt>最小 bulk ESS</dt><dd>{metric(diagnostics.minimumBulkEffectiveSampleSize, 0)}</dd></div>
        <div><dt>最小 tail ESS</dt><dd>{metric(diagnostics.minimumTailEffectiveSampleSize, 0)}</dd></div>
        <div>
          <dt>Y 方程 Bayesian R²</dt>
          <dd>{metric(result.posteriorPredictive?.yBayesianRSquared)}</dd>
        </div>
        <div>
          <dt>X 方程 Bayesian R²</dt>
          <dd>{metric(result.posteriorPredictive?.xBayesianRSquared)}</dd>
        </div>
      </dl>
      <p className="method-note">{result.methodNotice}</p>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              <th>动态参数</th><th>后验均值</th><th>后验 SD</th><th>95% CrI</th>
              <th>Pr(θ&gt;0)</th><th>R-hat</th><th>bulk ESS</th><th>tail ESS</th><th>MCSE</th>
            </tr>
          </thead>
          <tbody>
            {result.posteriorEffects?.map((effect) => (
              <tr key={effect.id}>
                <th>{effect.label}</th>
                <td>{metric(effect.estimate)}</td>
                <td>{metric(effect.posteriorSd)}</td>
                <td>[{metric(effect.lower)}, {metric(effect.upper)}]</td>
                <td>{metric(effect.probabilityPositive)}</td>
                <td>{metric(effect.rHat)}</td>
                <td>{metric(effect.bulkEffectiveSampleSize, 0)}</td>
                <td>{metric(effect.tailEffectiveSampleSize, 0)}</td>
                <td>{metric(effect.mcseMean)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {result.posteriorPredictive?.checks?.length ? (
        <>
          <h3>后验预测检验</h3>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>方程</th><th>统计量</th><th>观测</th><th>复制中位数</th><th>95%区间</th><th>Bayesian p</th></tr>
              </thead>
              <tbody>
                {result.posteriorPredictive.checks.map((check) => (
                  <tr key={`${check.equation}-${check.statistic}`}>
                    <th>{check.equation}</th><td>{check.statistic}</td>
                    <td>{metric(check.observed)}</td><td>{metric(check.replicatedMedian)}</td>
                    <td>[{metric(check.replicatedLower)}, {metric(check.replicatedUpper)}]</td>
                    <td>{metric(check.bayesianPValue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      {result.priorSensitivity?.scenarios?.length ? (
        <>
          <h3>先验敏感性</h3>
          <p className="method-note">{result.priorSensitivity.method}</p>
          <div className="table-wrap">
            <table className="result-table empirical-table">
              <thead>
                <tr><th>情景</th><th>先验 SD</th><th>重加权 ESS</th><th>推断变化数</th></tr>
              </thead>
              <tbody>
                {result.priorSensitivity.scenarios.map((scenario) => (
                  <tr key={scenario.scenario}>
                    <th>{scenario.scenario}</th>
                    <td>{metric(scenario.priorMeanSd)}</td>
                    <td>{metric(scenario.reweightingEffectiveSampleSize, 0)}</td>
                    <td>{scenario.effects.filter((effect) => effect.inferenceChanged).length}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
      <DiaryDsemPlots parameters={result.posteriorDraws ?? []} />
    </section>
  )
}
