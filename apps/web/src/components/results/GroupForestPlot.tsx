import { memo } from 'react'
import type { InvarianceResult } from '../../types'

interface GroupForestPlotProps {
  invarianceResult: InvarianceResult
}

export const GroupForestPlot = memo(function GroupForestPlot({ invarianceResult }: GroupForestPlotProps) {
  const groupParams = invarianceResult.groupParameters || []
  const pathComparisons = invarianceResult.pathComparisons || []

  if (groupParams.length === 0) {
    return <div className="alert alert-info">暂无多群组参数数据用于渲染森林图</div>
  }

  // Collect unique structural path keys (e.g. "X -> Y")
  const pathKeys = Array.from(
    new Set(groupParams.flatMap((g) => g.paths.map((p) => `${p.from} → ${p.to}`)))
  )

  return (
    <div className="group-forest-plot-container card p-4">
      <div className="section-heading mb-3">
        <div>
          <p className="eyebrow">Visual Cross-Group Path Comparison</p>
          <h4>多群组结构路径森林图 (Group Path Forest Plot)</h4>
        </div>
      </div>

      <div className="forest-plot-grid">
        {pathKeys.map((pathKey) => {
          const [from, to] = pathKey.split(' → ')
          const comparisons = pathComparisons.filter(
            (c) => c.from === from && c.to === to
          )

          // Gather all group estimates for this path
          const groupEstimates = groupParams.map((g) => {
            const p = g.paths.find((item) => item.from === from && item.to === to)
            return {
              group: g.group,
              estimate: p?.estimate ?? null,
              ciLower: p?.ciLower ?? null,
              ciUpper: p?.ciUpper ?? null,
              pValue: p?.pValue ?? null,
            }
          })

          // Calculate min/max range for SVG rendering
          const axisValues = groupEstimates.flatMap((g) =>
            [g.estimate, g.ciLower, g.ciUpper].filter(
              (value): value is number => typeof value === 'number' && Number.isFinite(value)
            )
          )
          const minVal = axisValues.length > 0
            ? Math.min(-0.2, Math.floor(Math.min(...axisValues) * 10) / 10)
            : -0.2
          const maxVal = axisValues.length > 0
            ? Math.max(0.8, Math.ceil(Math.max(...axisValues) * 10) / 10)
            : 0.8

          const svgWidth = 500
          const rowHeight = 35
          const svgHeight = groupEstimates.length * rowHeight + 40

          const getX = (val: number) => {
            const ratio = (val - minVal) / (maxVal - minVal)
            return 100 + ratio * 360
          }

          const zeroX = getX(0)

          return (
            <div key={pathKey} className="forest-path-card mb-4 border rounded p-3">
              <div className="d-flex justify-content-between align-items-center mb-2">
                <h5 className="m-0">路径: <strong>{pathKey}</strong></h5>
                {comparisons.length > 0 && (
                  <div className="wald-test-badges">
                    {comparisons.map((c) => (
                      <span key={`${c.groupA}-${c.groupB}`} className={`badge ms-2 ${c.pValue && c.pValue < .05 ? 'bg-danger' : 'bg-secondary'}`}>
                        {c.groupA} vs {c.groupB} ΔB={c.difference.toFixed(3)} (p={c.pValue !== null ? (c.pValue < .001 ? '<.001' : c.pValue.toFixed(3)) : '—'})
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <svg width={svgWidth} height={svgHeight} className="forest-svg" role="img" aria-label="多群组结构路径森林图">
                {/* 零值参考线 */}
                <line x1={zeroX} y1={20} x2={zeroX} y2={svgHeight - 20} stroke="#94a3b8" strokeDasharray="3,3" />

                {/* 刻度尺 */}
                <line x1={100} y1={svgHeight - 20} x2={460} y2={svgHeight - 20} stroke="#cbd5e1" />
                <text x={100} y={svgHeight - 5} fontSize="11" fill="#64748b" textAnchor="middle">{minVal.toFixed(1)}</text>
                <text x={zeroX} y={svgHeight - 5} fontSize="11" fill="#64748b" textAnchor="middle">0.0</text>
                <text x={460} y={svgHeight - 5} fontSize="11" fill="#64748b" textAnchor="middle">{maxVal.toFixed(1)}</text>

                {/* 群组估计点与 CI */}
                {groupEstimates.map((ge, idx) => {
                  const y = 30 + idx * rowHeight
                  const estimateAvailable = typeof ge.estimate === 'number' && Number.isFinite(ge.estimate)
                  const intervalAvailable =
                    estimateAvailable &&
                    typeof ge.ciLower === 'number' && Number.isFinite(ge.ciLower) &&
                    typeof ge.ciUpper === 'number' && Number.isFinite(ge.ciUpper)
                  const estX = estimateAvailable ? getX(ge.estimate as number) : null
                  const lowX = intervalAvailable ? getX(ge.ciLower as number) : null
                  const highX = intervalAvailable ? getX(ge.ciUpper as number) : null

                  return (
                    <g key={ge.group}>
                      {/* 群组名称 */}
                      <text x={90} y={y + 4} fontSize="12" fontWeight="600" fill="#334155" textAnchor="end">
                        {ge.group}
                      </text>

                      {estimateAvailable && estX !== null ? (
                        <>
                          {intervalAvailable && lowX !== null && highX !== null ? (
                            <>
                              {/* 置信区间来自后端结果；缺失时不在前端重算。 */}
                              <line x1={lowX} y1={y} x2={highX} y2={y} stroke="#2563eb" strokeWidth="2" />
                              <line x1={lowX} y1={y - 4} x2={lowX} y2={y + 4} stroke="#2563eb" strokeWidth="1.5" />
                              <line x1={highX} y1={y - 4} x2={highX} y2={y + 4} stroke="#2563eb" strokeWidth="1.5" />
                            </>
                          ) : null}

                          {/* 估计值方块 */}
                          <rect x={estX - 4} y={y - 4} width={8} height={8} fill="#1d4ed8" rx="1" />

                          {/* 数值标签 */}
                          <text x={(highX ?? estX) + 10} y={y + 4} fontSize="11" fill="#475569">
                            B={ge.estimate?.toFixed(3)} {intervalAvailable ? `[${ge.ciLower?.toFixed(2)}, ${ge.ciUpper?.toFixed(2)}]` : '[CI 不可用]'}
                          </text>
                        </>
                      ) : (
                        <text x={100} y={y + 4} fontSize="11" fill="#64748b">
                          估计值不可用
                        </text>
                      )}
                    </g>
                  )
                })}
              </svg>
            </div>
          )
        })}
      </div>
    </div>
  )
})
