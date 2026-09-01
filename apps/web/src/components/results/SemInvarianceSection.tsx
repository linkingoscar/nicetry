import { ScrollableResultTable } from '../shared/ScrollableResultTable'
import type { ResultBundle } from '../../types'
import { GroupForestPlot } from './GroupForestPlot'
import { InvarianceLadderView } from './InvarianceLadderView'
import { ModelImpliedPredictionPlot } from './ModelImpliedPredictionPlot'
import { PathCoefficientForestPlot } from './PathCoefficientForestPlot'
import { formatNumber, invarianceApaSection } from './resultSemSectionUtils'
import styles from './ResultSemSection.module.css'

interface SemInvarianceSectionProps {
  result: ResultBundle
}

export function SemInvarianceSection({ result }: SemInvarianceSectionProps) {
  const invarianceResult = result.invarianceResult
  if (!invarianceResult) return null

  return (
    <section className="equation-result">
      <strong>测量等值性检验 (Multi-Group Invariance Test)</strong>
      {invarianceApaSection(result.apaTables) ? (
        <div className="export-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={() => navigator.clipboard.writeText(invarianceApaSection(result.apaTables))}
          >
            复制等值性 APA 表
          </button>
          <a
            download="measurement-invariance-apa-table.md"
            href={`data:text/markdown;charset=utf-8,${encodeURIComponent(invarianceApaSection(result.apaTables))}`}
          >
            下载 APA 表
          </a>
        </div>
      ) : null}
      {invarianceResult.groupSizes ? (
        <p className="method-note">
          分组样本量：{Object.entries(invarianceResult.groupSizes)
            .map(([group, size]) => `${group} (n=${size})`)
            .join('；')}
        </p>
      ) : null}

      <div className={styles.invarianceFitBlock}>
        <span className="eyebrow eyebrow-block">等值性模型拟合指数对比</span>
        <ScrollableResultTable className="effect-table-wrap" label="等值性模型拟合指数对比表">
          <table className="result-table">
            <thead>
              <tr>
                <th>模型阶段</th>
                <th>等值限制</th>
                <th>Chi-Square</th>
                <th>df</th>
                <th>CFI</th>
                <th>TLI</th>
                <th>RMSEA</th>
              </tr>
            </thead>
            <tbody>
              {invarianceResult.models.map((m) => (
                <tr key={m.model}>
                  <th scope="row">{m.model.toUpperCase()}</th>
                  <td>
                    {m.constraints && m.constraints.length > 0
                      ? m.constraints.map((constraint) => ({ loadings: '载荷', intercepts: '截距', thresholds: '阈值', residuals: '残差' })[constraint]).join(' + ')
                      : '形态等值（无限制）'}
                  </td>
                  <td>{formatNumber(m.fitIndices.chiSquare)}</td>
                  <td>{m.fitIndices.df}</td>
                  <td>{formatNumber(m.fitIndices.cfi)}</td>
                  <td>{formatNumber(m.fitIndices.tli)}</td>
                  <td>{formatNumber(m.fitIndices.rmsea)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      </div>

      <div>
        <span className="eyebrow eyebrow-block">增量差异检验与学术判定</span>
        <ScrollableResultTable className="effect-table-wrap" label="增量差异检验表">
          <table className="result-table">
            <thead>
              <tr>
                <th>模型对比</th>
                <th>Δχ²</th>
                <th>Δdf</th>
                <th>p 值</th>
                <th>ΔCFI</th>
                <th>ΔRMSEA</th>
                <th>学术判定</th>
              </tr>
            </thead>
            <tbody>
              {invarianceResult.comparisons.map((c) => (
                <tr key={c.comparison}>
                  <th scope="row">{c.comparison.toUpperCase().replace('_VS_', ' vs ')}</th>
                  <td>{formatNumber(c.deltaChiSquare)}</td>
                  <td>{c.deltaDf}</td>
                  <td>{typeof c.pValue === 'number' ? (c.pValue < 0.001 ? '< .001' : c.pValue.toFixed(3)) : '—'}</td>
                  <td className={typeof c.deltaCfi === 'number' && c.deltaCfi < -0.01 ? 'table-row-warning' : 'table-row-success'}>{formatNumber(c.deltaCfi)}</td>
                  <td className={typeof c.deltaRmsea === 'number' && c.deltaRmsea > 0.015 ? 'table-row-warning' : 'table-row-success'}>{formatNumber(c.deltaRmsea)}</td>
                  <td>
                    <span className={`invariance-status-tag ${c.invarianceHolds === null ? 'is-unknown' : c.invarianceHolds ? 'is-pass' : 'is-fail'}`}>
                      {c.invarianceHolds === null ? '不可判定' : c.invarianceHolds ? '变化准则通过' : '变化准则未通过'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      </div>
      {invarianceResult.structuralComparison ? (
        <div className={styles.subSection}>
          <span className="eyebrow">结构路径等值模型</span>
          <p>
            χ²={formatNumber(invarianceResult.structuralComparison.fitIndices.chiSquare)}，
            df={invarianceResult.structuralComparison.fitIndices.df ?? '—'}；
            相对截距/阈值等值模型 Δχ²={formatNumber(invarianceResult.structuralComparison.deltaChiSquare)}，
            Δdf={invarianceResult.structuralComparison.deltaDf ?? '—'}，
            p={formatNumber(invarianceResult.structuralComparison.pValue)}。
          </p>
        </div>
      ) : null}

      {(invarianceResult.groupParameters?.length ?? 0) > 0 ? (
        <div className={styles.subSection}>
          <span className="eyebrow">逐组结构路径（配置模型）</span>
          <ScrollableResultTable className="effect-table-wrap" label="逐组结构路径表">
            <table className="result-table">
              <thead>
                <tr><th>组别</th><th>路径</th><th>B</th><th>SE</th><th>p</th><th>β</th></tr>
              </thead>
              <tbody>
                {invarianceResult.groupParameters?.flatMap((group) =>
                  group.paths.map((path) => (
                    <tr key={`${group.group}:${path.from}:${path.to}`}>
                      <th scope="row">{group.group}</th>
                      <td>{path.from} → {path.to}</td>
                      <td>{formatNumber(path.estimate)}</td>
                      <td>{formatNumber(path.standardError)}</td>
                      <td>{formatNumber(path.pValue)}</td>
                      <td>{formatNumber(path.stdAll)}</td>
                    </tr>
                  )))}
              </tbody>
            </table>
          </ScrollableResultTable>
          <PathCoefficientForestPlot groups={invarianceResult.groupParameters ?? []} />
        </div>
      ) : null}

      {(invarianceResult.pathComparisons?.length ?? 0) > 0 ? (
        <div className={styles.subSection}>
          <span className="eyebrow">单路径跨组差异检验</span>
          <ScrollableResultTable className="effect-table-wrap" label="单路径跨组差异检验表">
            <table className="result-table">
              <thead>
                <tr><th>路径</th><th>组别差</th><th>ΔB</th><th>SE</th><th>z</th><th>p</th><th>95% CI</th></tr>
              </thead>
              <tbody>
                {invarianceResult.pathComparisons?.map((comparison) => (
                  <tr key={`${comparison.from}:${comparison.to}:${comparison.groupA}:${comparison.groupB}`}>
                    <th scope="row">{comparison.from} → {comparison.to}</th>
                    <td>{comparison.groupA} − {comparison.groupB}</td>
                    <td>{formatNumber(comparison.difference)}</td>
                    <td>{formatNumber(comparison.standardError)}</td>
                    <td>{formatNumber(comparison.statistic)}</td>
                    <td>{formatNumber(comparison.pValue)}</td>
                    <td>[{formatNumber(comparison.ciLower)}, {formatNumber(comparison.ciUpper)}]</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollableResultTable>
          <p className="method-note">差异检验比较未标准化路径系数；只有在载荷等值性证据足够时才解释潜变量路径的跨组差异。</p>
        </div>
      ) : null}

      <div className={styles.ladderBlock}>
        <InvarianceLadderView invarianceResult={invarianceResult} />
        <GroupForestPlot invarianceResult={invarianceResult} />
      </div>
      {(invarianceResult.partialInvarianceReleases?.length ?? 0) > 0 ? (
        <div className={styles.subSection}>
          <span className="eyebrow">手动部分等值释放记录</span>
          <ul>
            {invarianceResult.partialInvarianceReleases?.map((release) => (
              <li key={`${release.stage}:${release.constraint}:${release.latentId}:${release.indicatorId}`}>
                {release.stage} · {release.constraint} · {release.latentId ? `${release.latentId} =~ ` : ''}
                {release.indicatorId}：{release.rationale}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {(invarianceResult.predictionPlots?.length ?? 0) > 0 ? (
        <div className={styles.subSection}>
          <span className="eyebrow">满足适用条件的模型隐含预测线</span>
          {invarianceResult.predictionPlots?.map((plot) => (
            <ModelImpliedPredictionPlot key={`${plot.from}:${plot.to}`} plot={plot} />
          ))}
        </div>
      ) : null}
      <p className="method-note">ΔCFI 与 ΔRMSEA 作为递进证据展示，不单独替代模型识别、理论合理性和参数诊断；载荷等值不足时不解释跨组结构差异，截距/阈值等值不足时不直接比较潜均值。</p>
    </section>
  )
}
