import type { InvarianceResult } from '../../types'

type PredictionPlot = NonNullable<InvarianceResult['predictionPlots']>[number]

const palette = ['#2563a6', '#a46f00', '#c45a16', '#24387a', '#a04473']
const dashPatterns = ['', '7 4', '2 3', '10 3 2 3', '5 5']

function points(
  xValues: number[],
  yValues: number[],
  x: (value: number) => number,
  y: (value: number) => number,
) {
  return xValues.map((value, index) => `${x(value)},${y(yValues[index])}`).join(' ')
}

export function ModelImpliedPredictionPlot({ plot }: { plot: PredictionPlot }) {
  const allX = plot.groups.flatMap((group) => group.xValues)
  const allY = plot.groups.flatMap((group) => [...group.ciLower, ...group.ciUpper])
  const xMin = Math.min(...allX)
  const xMax = Math.max(...allX)
  const yMin = Math.min(...allY)
  const yMax = Math.max(...allY)
  const width = 760
  const height = 410
  const left = 72
  const right = 28
  const top = 54
  const bottom = 58
  const x = (value: number) => left + ((value - xMin) / Math.max(xMax - xMin, 1e-12)) * (width - left - right)
  const y = (value: number) => top + ((yMax - value) / Math.max(yMax - yMin, 1e-12)) * (height - top - bottom)

  return (
    <figure style={{ display: 'grid', gap: '10px', margin: '14px 0 0', padding: '14px', overflowX: 'auto', background: '#fff', border: '1px solid #dfe1e7', borderRadius: '9px' }}>
      <figcaption style={{ display: 'grid', gap: '3px', color: '#19223f' }}>
        <strong>{plot.outcomeLabel} 对 {plot.predictorLabel} 的模型隐含预测</strong>
        <span style={{ color: '#595d6b', fontSize: '12px', lineHeight: 1.5 }}>观测尺度、单一预测方程；实线/虚线区分组别，阴影为 {Math.round(plot.confidenceLevel * 100)}% 置信区间。</span>
      </figcaption>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label={`${plot.outcomeLabel} 对 ${plot.predictorLabel} 的多组模型隐含预测线`}
        style={{ width: '100%', minWidth: '620px' }}
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const value = yMin + fraction * (yMax - yMin)
          return (
            <g key={fraction}>
              <line x1={left} x2={width - right} y1={y(value)} y2={y(value)} stroke="#e2e3e8" />
              <text x={left - 10} y={y(value) + 4} textAnchor="end" fill="#595d6b" fontSize="10">
                {value.toFixed(2)}
              </text>
            </g>
          )
        })}
        {plot.groups.map((group, index) => {
          const color = palette[index % palette.length]
          const upper = points(group.xValues, group.ciUpper, x, y)
          const lower = points([...group.xValues].reverse(), [...group.ciLower].reverse(), x, y)
          return (
            <g key={group.group}>
              <polygon points={`${upper} ${lower}`} fill={color} opacity="0.10" />
              <polyline
                points={points(group.xValues, group.predictedValues, x, y)}
                fill="none"
                stroke={color}
                strokeWidth="2.5"
                strokeDasharray={dashPatterns[index % dashPatterns.length]}
              />
              <text
                x={x(group.xValues[group.xValues.length - 1]) - 4}
                y={y(group.predictedValues[group.predictedValues.length - 1]) - 8}
                textAnchor="end"
                fill={color}
                fontSize="11"
                fontWeight="700"
              >
                {group.group}
              </text>
            </g>
          )
        })}
        <line x1={left} x2={left} y1={top} y2={height - bottom} stroke="#595d6b" />
        <line x1={left} x2={width - right} y1={height - bottom} y2={height - bottom} stroke="#595d6b" />
        <text x={left} y={height - bottom + 18} fill="#595d6b" fontSize="10">{xMin.toFixed(2)}</text>
        <text x={width - right} y={height - bottom + 18} fill="#595d6b" fontSize="10" textAnchor="end">{xMax.toFixed(2)}</text>
        <text x={(left + width - right) / 2} y={height - 12} fill="#404554" fontSize="11" textAnchor="middle">
          {plot.predictorLabel}
        </text>
        <text x={16} y={(top + height - bottom) / 2} fill="#404554" fontSize="11" textAnchor="middle" transform={`rotate(-90 16 ${(top + height - bottom) / 2})`}>
          {plot.outcomeLabel}
        </text>
      </svg>
      <p className="method-note">{plot.method}</p>
    </figure>
  )
}
