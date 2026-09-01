import type { DiaryMultilevelResult, LongitudinalPanelResult } from '../../types'

interface MethodRobustnessResultProps {
  longitudinal?: LongitudinalPanelResult['robustnessChecks']
  diary?: DiaryMultilevelResult['robustnessChecks']
  metric: (value: number | null | undefined, digits?: number) => string
}

export function MethodRobustnessResult({
  longitudinal,
  diary,
  metric,
}: MethodRobustnessResultProps) {
  if ((!longitudinal?.length || longitudinal.length < 2) && (!diary?.length || diary.length < 2)) {
    return null
  }
  return (
    <div className="longitudinal-evidence-stack">
      <h3>自动稳健性矩阵</h3>
      {longitudinal?.length ? (
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead>
              <tr><th>情景</th><th>模型</th><th>N</th><th>缺失</th><th>路径等值</th><th>CFI</th><th>RMSEA</th><th>有效</th></tr>
            </thead>
            <tbody>
              {longitudinal.map((row) => (
                <tr key={row.scenario}>
                  <th>{row.scenario}</th><td>{row.modelType}</td><td>{row.sampleSize}</td>
                  <td>{row.missingMethod}</td><td>{row.constrainedAcrossTime ? '是' : '否'}</td>
                  <td>{metric(row.fitIndices.cfi)}</td><td>{metric(row.fitIndices.rmsea)}</td>
                  <td>{row.validForInterpretation ? '是' : '否'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {diary?.length ? (
        <div className="table-wrap">
          <table className="result-table empirical-table">
            <thead>
              <tr><th>情景</th><th>模型</th><th>N</th><th>时间效应</th><th>残差</th><th>随机斜率</th><th>有效</th></tr>
            </thead>
            <tbody>
              {diary.map((row) => (
                <tr key={row.scenario}>
                  <th>{row.scenario}</th><td>{row.modelLabel}</td><td>{row.sampleSize}</td>
                  <td>{row.temporalEffect ?? '—'}</td><td>{row.residualStructure ?? '—'}</td>
                  <td>{row.randomSlope === null ? '—' : row.randomSlope ? '是' : '否'}</td>
                  <td>{row.validForInterpretation ? '是' : '否'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      <p className="method-note">
        稳健性情景改变模型假设；应比较效应方向、区间和结论，而不能仅按显著性筛选结果。
      </p>
    </div>
  )
}
