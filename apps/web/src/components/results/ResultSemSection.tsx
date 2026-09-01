import { ScrollableResultTable } from '../shared/ScrollableResultTable'
import type { ResultBundle } from '../../types'
import { confidenceLabel, formatCI, formatNumber } from './resultSemSectionUtils'
import { SemInvarianceSection } from './SemInvarianceSection'

interface ResultSemSectionProps {
  result: ResultBundle
}

export function ResultSemSection({ result }: ResultSemSectionProps) {
  const semResult = result.semResult
  if (!semResult) return null

  const ciLabel = confidenceLabel(result.provenance?.confidenceLevel)

  return (
    <div className="sem-results-container">
      {semResult.requiresManualReview || result.requiresManualReview ? (
        <div className="error-banner" role="status">
          SEM 当前需要人工复核，不能直接作为论文主分析发布：{(semResult.publicationEligibilityReasons ?? result.publicationEligibilityReasons ?? []).join('、') || '存在异常解或估计边界。'}
        </div>
      ) : null}
      <p className="method-note">SEM 结果默认按关联性证据解释；横截面模型不生成“导致/机制/因果效应”文案。估计器、缺失处理与数值参考矩阵均保存在结果 provenance 中。</p>
      {/* 1. 拟合指数 */}
      <section className="equation-result">
        <strong>拟合优度指数 (Fit Indices)</strong>
        {semResult.modelStructure.higherOrderLatents.length > 0 ? (
          <p className="method-note">
            高阶潜变量：{semResult.modelStructure.higherOrderLatents.join('、')}；
            其载荷以低阶潜变量为指标单独标识。
          </p>
        ) : null}
        <div className="stat-grid" aria-live="polite">
          <div className="stat">
            <span>Chi-Square (df, p)</span>
            <strong>
              {formatNumber(semResult.fitIndices.chiSquare)}{' '}
              <small className="stat-note-small">
                ({semResult.fitIndices.df ?? '—'}, {typeof semResult.fitIndices.pValue === 'number' && semResult.fitIndices.pValue < 0.001 ? '<.001' : formatNumber(semResult.fitIndices.pValue)})
              </small>
            </strong>
          </div>
          <div className="stat">
            <span>CFI</span>
            <strong>{formatNumber(semResult.fitIndices.cfi)}</strong>
          </div>
          <div className="stat">
            <span>TLI</span>
            <strong>{formatNumber(semResult.fitIndices.tli)}</strong>
          </div>
          <div className="stat">
            <span>RMSEA</span>
            <strong>{formatNumber(semResult.fitIndices.rmsea)}</strong>
          </div>
          <div className="stat">
            <span>SRMR</span>
            <strong>{formatNumber(semResult.fitIndices.srmr)}</strong>
          </div>
        </div>

        {semResult.fitIndices.robustChiSquare !== undefined && semResult.fitIndices.robustChiSquare !== null ? (
          <div className="robust-metrics-card">
            <strong>Robust / WLSMV 修正拟合指数:</strong> Robust Chi-Square = {formatNumber(semResult.fitIndices.robustChiSquare)} (df={semResult.fitIndices.robustDf}, p={typeof semResult.fitIndices.robustPValue === 'number' && semResult.fitIndices.robustPValue < 0.001 ? '<.001' : formatNumber(semResult.fitIndices.robustPValue)}); Robust CFI = {formatNumber(semResult.fitIndices.robustCfi)}; Robust TLI = {formatNumber(semResult.fitIndices.robustTli)}; Robust RMSEA = {formatNumber(semResult.fitIndices.robustRmsea)}.
          </div>
        ) : null}
      </section>

      {/* 2. 测量载荷 (Measurement Loadings) */}
      <section className="equation-result">
        <strong>测量模型载荷 (Measurement Loadings)</strong>
        <ScrollableResultTable className="effect-table-wrap" label="测量模型载荷表">
          <table className="result-table">
            <thead>
              <tr>
                <th>潜变量</th>
                <th>题项/低阶因子</th>
                <th>层级</th>
                <th>估算值 (B)</th>
                <th>标准误 (SE)</th>
                <th>z 临界比</th>
                <th>p 值</th>
                <th>标准化载荷 (std.all)</th>
                <th>{ciLabel}</th>
              </tr>
            </thead>
            <tbody>
              {semResult.loadings.map((loading) => (
                <tr key={`${loading.latentId}:${loading.indicatorId}`}>
                  <th scope="row">{loading.latentId}</th>
                  <td>{loading.indicatorId}</td>
                  <td>{loading.level === 'higher_order' ? '高阶载荷' : '一阶载荷'}</td>
                  <td>{formatNumber(loading.estimate)}</td>
                  <td>{loading.standardError !== null ? formatNumber(loading.standardError) : '—'}</td>
                  <td>{loading.statistic !== null ? formatNumber(loading.statistic) : '—'}</td>
                  <td>
                    {loading.pValue !== null
                      ? (loading.pValue < 0.001 ? '< .001' : loading.pValue.toFixed(3))
                      : '—'}
                  </td>
                  <td>{formatNumber(loading.stdAll)}</td>
                  <td>{formatCI(loading.ciLower, loading.ciUpper)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      </section>

      {/* 3. 结构路径 (Structural Paths) */}
      <section className="equation-result">
        <strong>结构关系路径 (Structural Paths)</strong>
        <ScrollableResultTable className="effect-table-wrap" label="结构关系路径表">
          <table className="result-table">
            <thead>
              <tr>
                <th>路径起点 (Predictor)</th>
                <th>路径终点 (Outcome)</th>
                <th>估算值 (B)</th>
                <th>标准误 (SE)</th>
                <th>z 临界比</th>
                <th>p 值</th>
                <th>标准化系数 (β)</th>
                <th>{ciLabel}</th>
              </tr>
            </thead>
            <tbody>
              {semResult.paths.map((path) => (
                <tr key={`${path.from}:${path.to}`}>
                  <th scope="row">{path.from}</th>
                  <td>{path.to}</td>
                  <td>{formatNumber(path.estimate)}</td>
                  <td>{path.standardError !== null ? formatNumber(path.standardError) : '—'}</td>
                  <td>{path.statistic !== null ? formatNumber(path.statistic) : '—'}</td>
                  <td>
                    {path.pValue !== null
                      ? (path.pValue < 0.001 ? '< .001' : path.pValue.toFixed(3))
                      : '—'}
                  </td>
                  <td>{formatNumber(path.stdAll)}</td>
                  <td>{formatCI(path.ciLower, path.ciUpper)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      </section>

      {/* 4. 信效度指标 */}
      <section className="equation-result">
        <strong>信度与效度评估 (Reliability & Validity)</strong>
        <ScrollableResultTable className="effect-table-wrap" label="信度与效度评估表">
          <table className="result-table">
            <thead>
              <tr>
                <th>潜变量</th>
                <th>Cronbach's α</th>
                <th>α 样本量 N</th>
                <th>McDonald's ω</th>
                <th>组合信度 (CR)</th>
                <th>平均方差提取值 (AVE)</th>
              </tr>
            </thead>
            <tbody>
              {semResult.reliability.map((rel) => {
                const crSuppressed = rel.compositeReliabilityReason === 'suppressed_correlated_residuals'
                return (
                  <tr key={rel.latentId}>
                    <th scope="row">{rel.latentId}</th>
                    <td>{formatNumber(rel.cronbachAlpha)}</td>
                    <td>{rel.alphaSampleSize ?? '—'}</td>
                    <td>{crSuppressed ? '—' : formatNumber(rel.mcdonaldOmega)}</td>
                    <td className={crSuppressed ? 'table-row-warning' : undefined}>
                      {crSuppressed ? '—（存在相关残差）' : formatNumber(rel.compositeReliability)}
                    </td>
                    <td className={rel.ave !== null && rel.ave < 0.5 ? 'table-row-warning' : undefined}>
                      {formatNumber(rel.ave)}{' '}
                      {rel.ave !== null && rel.ave < 0.5 ? <small>{'(< 0.5)'}</small> : null}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </ScrollableResultTable>
        <p className="method-note">
          CR 与 AVE 是收敛效度证据的一部分；界面不依据单一阈值自动判定量表有效。
          α 基于完整案例（listwise）计算，其样本量可能与主拟合（如 FIML）不同，见 α 样本量列；
          潜变量指标间存在自由相关残差时 CR/ω 公式不再成立，结果置 null 并要求人工复核。
        </p>
      </section>

      {/* 5. 多组等值性检验 (Invariance Results) */}
      <SemInvarianceSection result={result} />
    </div>
  )
}
