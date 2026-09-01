import type { DiaryMultilevelResult } from '../../types'

interface DiaryCenteringTrendResultProps {
  result: DiaryMultilevelResult
  metric: (value: number | null | undefined, digits?: number) => string
  probability: (value: number | null | undefined) => string
}

export function DiaryCenteringTrendResult({
  result,
  metric,
  probability,
}: DiaryCenteringTrendResultProps) {
  const protocol = result.centeringProtocol
  const trend = result.timeTrendTest
  if (!protocol && !trend) return null

  return (
    <div className="longitudinal-evidence-stack">
      {protocol ? (
        <section className="analysis-result-subsection" aria-labelledby="esm-centering-heading">
          <h3 id="esm-centering-heading">中心化协议</h3>
          <dl className="run-meta factor-meta">
            <div>
              <dt>Level-1 策略</dt>
              <dd>{protocol.level1Predictor.strategy}</dd>
            </div>
            <div>
              <dt>组内公式</dt>
              <dd>{protocol.level1Predictor.level1Formula}</dd>
            </div>
            <div>
              <dt>个人均值重入</dt>
              <dd>{protocol.level1Predictor.personMeanReintroduced ? '是' : '否'}</dd>
            </div>
            <div>
              <dt>被试间权重</dt>
              <dd>{protocol.level1Predictor.grandMeanWeighting ?? '不适用'}</dd>
            </div>
            {protocol.level2Moderator ? (
              <>
                <div><dt>Level-2 策略</dt><dd>{protocol.level2Moderator.strategy}</dd></div>
                <div>
                  <dt>Level-2 参照值</dt>
                  <dd>{metric(protocol.level2Moderator.reference)}</dd>
                </div>
              </>
            ) : null}
          </dl>
          <p className="method-note">{protocol.interpretation}</p>
          {protocol.crossLevelInteractions.length ? (
            <p className="method-note">
              跨层交互：{protocol.crossLevelInteractions.join('；')}
            </p>
          ) : null}
        </section>
      ) : null}
      {trend ? (
        <section className="analysis-result-subsection" aria-labelledby="esm-time-trend-heading">
          <h3 id="esm-time-trend-heading">时间趋势联合检验</h3>
          <dl className="run-meta factor-meta">
            <div><dt>原点策略</dt><dd>{trend.originStrategy}</dd></div>
            <div><dt>原点值</dt><dd>{metric(trend.originValue)}</dd></div>
            <div><dt>线性斜率</dt><dd>{metric(trend.linearSlopeAtOrigin)}</dd></div>
            <div><dt>二次项</dt><dd>{metric(trend.quadraticCoefficient)}</dd></div>
            <div>
              <dt>联合 Wald</dt>
              <dd>χ²({trend.degreesOfFreedom}) = {metric(trend.statistic)}</dd>
            </div>
            <div><dt>p</dt><dd>{probability(trend.pValue)}</dd></div>
            {trend.turningPoint !== null ? (
              <div>
                <dt>转折点</dt>
                <dd>
                  {metric(trend.turningPoint)}
                  {trend.turningPointInObservedRange ? '（样本范围内）' : '（样本范围外）'}
                </dd>
              </div>
            ) : null}
          </dl>
        </section>
      ) : null}
    </div>
  )
}
