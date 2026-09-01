import type {
  DiaryPowerResult,
  LongitudinalPowerResult,
} from '../../types'

interface MonteCarloPowerResultProps {
  longitudinal?: LongitudinalPowerResult
  diary?: DiaryPowerResult
  metric: (value: number | null | undefined, digits?: number) => string
}

export function MonteCarloPowerResult({
  longitudinal,
  diary,
  metric,
}: MonteCarloPowerResultProps) {
  if (!longitudinal && !diary) return null
  if (longitudinal) {
    return (
      <div className="longitudinal-evidence-stack">
        <div className="section-heading">
          <h3>RI-CLPM 蒙特卡洛功效</h3>
          <span className={`status-chip ${longitudinal.validForPlanning ? '' : 'is-warning'}`}>
            {longitudinal.validForPlanning ? '可用于规划' : '需检查模拟'}
          </span>
        </div>
        <p className="method-note">
          {longitudinal.replications} 次模拟；α={metric(longitudinal.alpha)}；
          目标功效={metric(longitudinal.targetPower)}；
          推荐样本量={longitudinal.recommendedSampleSize ?? '候选范围内未达到'}。
        </p>
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead>
              <tr>
                <th>N</th><th>方向</th><th>真值</th><th>平均估计</th>
                <th>偏差</th><th>经验 SE</th><th>覆盖率 (MCSE)</th><th>功效 (MCSE)</th>
              </tr>
            </thead>
            <tbody>
              {longitudinal.results.map((row) => (
                <tr key={`${row.sampleSize}-${row.direction}`}>
                  <th>{row.sampleSize}</th><td>{row.directionLabel}</td>
                  <td>{metric(row.populationValue)}</td><td>{metric(row.averageEstimate)}</td>
                  <td>{metric(row.bias)}</td><td>{metric(row.empiricalStandardError)}</td>
                  <td>{metric(row.coverage)} ({metric(row.coverageMcse)})</td>
                  <td>{metric(row.power)} ({metric(row.powerMcse)})</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {longitudinal.estimationProblems.length || longitudinal.warnings.length ? (
          <p className="method-note">
            模拟估计问题 {longitudinal.estimationProblems.length} 项；
            警告 {longitudinal.warnings.length} 项。完整内容已写入导出证据表。
          </p>
        ) : null}
      </div>
    )
  }
  if (!diary) return null
  return (
    <div className="longitudinal-evidence-stack">
      <div className="section-heading">
        <h3>ESM 蒙特卡洛功效</h3>
        <span className={`status-chip ${diary.validForPlanning ? '' : 'is-warning'}`}>
          {diary.validForPlanning ? '可用于规划' : '需检查模拟'}
        </span>
      </div>
      <p className="method-note">
        目标参数：{diary.targetParameter}；{diary.replications} 次模拟；
        推荐设计={diary.recommendation
          ? `${diary.recommendation.personCount} 人 × ${diary.recommendation.observationsPerPerson} 次`
          : '候选范围内未同时达到目标功效与 95% 收敛率'}。
      </p>
      <div className="table-wrap">
        <table className="result-table empirical-table">
          <thead>
            <tr>
              <th>人数</th><th>每人次数</th><th>总观测</th><th>功效 (MCSE)</th>
              <th>覆盖率 (MCSE)</th><th>偏差</th><th>收敛率</th><th>奇异拟合</th>
            </tr>
          </thead>
          <tbody>
            {diary.results.map((row) => (
              <tr key={`${row.personCount}-${row.observationsPerPerson}`}>
                <th>{row.personCount}</th><td>{row.observationsPerPerson}</td>
                <td>{row.totalObservations}</td>
                <td>{metric(row.power)} ({metric(row.powerMcse)})</td>
                <td>{metric(row.coverage)} ({metric(row.coverageMcse)})</td>
                <td>{metric(row.bias)}</td>
                <td>{metric(row.convergenceRate)}</td><td>{row.singularReplications}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
