interface EmmConfidencePlotProps {
  rows: Array<Record<string, unknown>>
}

interface EmmPoint {
  label: string
  estimate: number
  lower: number
  upper: number
}

const STATISTICAL_COLUMNS = new Set([
  'emmean', 'SE', 'df', 'lower.CL', 'upper.CL', 'asymp.LCL', 'asymp.UCL', '.wgt.',
])

function pointsFrom(rows: Array<Record<string, unknown>>): EmmPoint[] {
  return rows.flatMap((row) => {
    const estimate = row.emmean
    const lower = row['lower.CL'] ?? row['asymp.LCL']
    const upper = row['upper.CL'] ?? row['asymp.UCL']
    if (typeof estimate !== 'number' || typeof lower !== 'number' || typeof upper !== 'number') return []
    const label = Object.entries(row)
      .filter(([key, value]) => !STATISTICAL_COLUMNS.has(key) && ['string', 'number'].includes(typeof value))
      .map(([key, value]) => `${key}=${String(value)}`)
      .join(', ')
    return [{ label: label || 'EMM', estimate, lower, upper }]
  })
}

export function EmmConfidencePlot({ rows }: EmmConfidencePlotProps) {
  const titleId = useId()
  const descriptionId = useId()
  const points = pointsFrom(rows)
  if (points.length === 0) return null
  const minimum = Math.min(...points.map(({ lower }) => lower))
  const maximum = Math.max(...points.map(({ upper }) => upper))
  const span = maximum - minimum || 1
  const width = 760
  const labelWidth = 210
  const plotWidth = width - labelWidth - 40
  const rowHeight = 34
  const height = 54 + points.length * rowHeight
  const x = (value: number) => labelWidth + ((value - minimum) / span) * plotWidth

  return (
    <section className="adv-result-section" aria-label="Estimated marginal means confidence plot">
      <div>
        <h3>EMM 与置信区间</h3>
        <p className="muted">点为模型估计边际均值，横线为请求置信水平对应的区间；组间判断应使用 contrast 表。</p>
      </div>
      <div className="adv-emm-plot-wrap">
        <svg
          className="adv-emm-plot"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
        >
          <title id={titleId}>Estimated marginal means and confidence intervals</title>
          <desc id={descriptionId}>Model-based marginal means with lower and upper confidence limits. Exact values are available in the adjacent table.</desc>
          <line x1={labelWidth} x2={labelWidth + plotWidth} y1="28" y2="28" className="adv-emm-axis" />
          <text x={labelWidth} y="18" textAnchor="start" className="adv-emm-axis-label">{minimum.toFixed(3)}</text>
          <text x={labelWidth + plotWidth} y="18" textAnchor="end" className="adv-emm-axis-label">{maximum.toFixed(3)}</text>
          {points.map((point, index) => {
            const y = 48 + index * rowHeight
            return (
              <g key={`${point.label}:${point.estimate}`}>
                <text x="4" y={y + 4} className="adv-emm-label">{point.label}</text>
                <line x1={x(point.lower)} x2={x(point.upper)} y1={y} y2={y} className="adv-emm-interval" />
                <line x1={x(point.lower)} x2={x(point.lower)} y1={y - 5} y2={y + 5} className="adv-emm-cap" />
                <line x1={x(point.upper)} x2={x(point.upper)} y1={y - 5} y2={y + 5} className="adv-emm-cap" />
                <circle cx={x(point.estimate)} cy={y} r="4.5" className="adv-emm-point">
                  <title>{`${point.label}: ${point.estimate.toFixed(6)} [${point.lower.toFixed(6)}, ${point.upper.toFixed(6)}]`}</title>
                </circle>
              </g>
            )
          })}
        </svg>
      </div>
    </section>
  )
}
import { useId } from 'react'
