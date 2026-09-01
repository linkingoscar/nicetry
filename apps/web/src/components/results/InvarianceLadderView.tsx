import { memo } from 'react'
import type { InvarianceResult } from '../../types'

interface InvarianceLadderViewProps {
  invarianceResult: InvarianceResult
}

export const InvarianceLadderView = memo(function InvarianceLadderView({ invarianceResult }: InvarianceLadderViewProps) {
  const { models, comparisons, latentMeans } = invarianceResult

  const stageMap: Record<string, string> = {
    configural: '形态等值 (Configural)',
    metric: '弱等值/载荷等值 (Metric)',
    scalar: '强等值/截距等值 (Scalar)',
    strict: '严格等值/残差等值 (Strict)',
  }

  return (
    <div className="invariance-ladder-view">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Measurement Invariance Ladder</p>
          <h3>多群组测量等值性 5 阶梯检验</h3>
        </div>
      </div>

      {/* 5 阶段模型 Fit 展示 */}
      <div className="invariance-cards-grid">
        {models.map((m, idx) => {
          const comp = comparisons.find((c) => c.comparison.startsWith(m.model))
          return (
            <div key={m.model} className="invariance-stage-card">
              <div className="stage-header">
                <span className="stage-num">0{idx + 1}</span>
                <strong>{stageMap[m.model] || m.model}</strong>
              </div>

              <div className="stage-fit">
                <div>χ² = <strong>{m.fitIndices.chiSquare?.toFixed(2) ?? '—'}</strong> (df={m.fitIndices.df})</div>
                <div>CFI = <strong>{m.fitIndices.cfi?.toFixed(3) ?? '—'}</strong></div>
                <div>TLI = <strong>{m.fitIndices.tli?.toFixed(3) ?? '—'}</strong></div>
                <div>RMSEA = <strong>{m.fitIndices.rmsea?.toFixed(3) ?? '—'}</strong></div>
              </div>

              {comp && (
                <div className={`comp-badge ${comp.invarianceHolds ? 'is-pass' : 'is-warning'}`}>
                  <span>ΔCFI: {(comp.deltaCfi ?? 0) > 0 ? `+${comp.deltaCfi?.toFixed(3)}` : comp.deltaCfi?.toFixed(3)}</span>
                  <span>ΔRMSEA: {(comp.deltaRmsea ?? 0) > 0 ? `+${comp.deltaRmsea?.toFixed(3)}` : comp.deltaRmsea?.toFixed(3)}</span>
                  <span className="hold-status">
                    {comp.invarianceHolds ? '✓ 等值成立' : '⚠️ 需关注/释放部分等值'}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* 学术评价准则诊断 Alert */}
      <div className="alert-card diagnostic-alert-card info">
        <div className="alert-title">📚 学术判定标准 (Cheung & Rensvold, 2002; Meade et al., 2008)</div>
        <div className="alert-body">
          测量等值性检验不推荐仅依赖 $\Delta\chi^2$（易受大样本过度敏感影响）。常用经验法则：若 <strong>|ΔCFI| &le; .010</strong> 且 <strong>|ΔRMSEA| &le; .015</strong>，则可判定该阶梯等值性成立。若强等值 (Scalar) 成立，方可对潜均值差异做有意义的学术解释。
        </div>
      </div>

      {/* 潜均值差异估计 */}
      {latentMeans && latentMeans.length > 0 && (
        <div className="latent-means-section">
          <h4>潜均值跨组比较 (Latent Means Differences)</h4>
          <div className="table-responsive">
            <table className="table apa-table">
              <thead>
                <tr>
                  <th>分组</th>
                  <th>潜变量</th>
                  <th>相对均值估计</th>
                  <th>SE</th>
                  <th>P 值</th>
                  <th>95% 置信区间</th>
                  <th>备注</th>
                </tr>
              </thead>
              <tbody>
                {latentMeans.map((lm) => (
                  <tr key={`${lm.group}-${lm.latentId}`}>
                    <td><strong>{lm.group}</strong></td>
                    <td>{lm.latentId}</td>
                    <td>{lm.referenceGroup ? '0.000 (基准)' : lm.estimate.toFixed(3)}</td>
                    <td>{lm.referenceGroup ? '—' : lm.standardError?.toFixed(3) ?? '—'}</td>
                    <td>{lm.referenceGroup ? '—' : (lm.pValue !== null ? (lm.pValue < .001 ? '< .001' : lm.pValue.toFixed(3)) : '—')}</td>
                    <td>
                      {lm.referenceGroup ? '—' : `[${lm.ciLower?.toFixed(3)}, ${lm.ciUpper?.toFixed(3)}]`}
                    </td>
                    <td>
                      {lm.referenceGroup ? (
                        <span className="pill-chip">参照组 (Baseline)</span>
                      ) : lm.pValue && lm.pValue < .05 ? (
                        <span className="pill-chip is-good">显著均值差异</span>
                      ) : (
                        <span className="pill-chip">无显著差异</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
})
