import { useId, useRef, useState } from 'react'
import { formatAPAStat } from '../../utils/apaFormatter'
import { exportSvgAs300DpiPng, exportSvgAsFile } from '../../utils/figureExport'
import {
  JOURNAL_COLOR_PRESETS,
  type JournalColorPreset,
  JournalPresetSelector,
} from '../shared/JournalPresetSelector'

interface EmmConfidencePlotProps {
  rows: Array<Record<string, unknown>>
}
interface EmmPoint {
  label: string
  estimate: number
  lower: number
  upper: number
}

interface KeyedEmmPoint {
  key: string
  point: EmmPoint
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

function withStableKeys(points: EmmPoint[]): KeyedEmmPoint[] {
  const occurrences = new Map<string, number>()
  return points.map((point) => {
    const identity = JSON.stringify([point.label, point.estimate, point.lower, point.upper])
    const occurrence = occurrences.get(identity) ?? 0
    occurrences.set(identity, occurrence + 1)
    return { key: `emm-${identity}-${occurrence}`, point }
  })
}

export function EmmConfidencePlot({ rows }: EmmConfidencePlotProps) {
  const titleId = useId()
  const descriptionId = useId()
  const [preset, setPreset] = useState<JournalColorPreset>('emerald')
  const svgRef = useRef<SVGSVGElement>(null)

  const points = pointsFrom(rows)
  if (points.length === 0) return null
  const keyedPoints = withStableKeys(points)
  const minimum = Math.min(...points.map(({ lower }) => lower))
  const maximum = Math.max(...points.map(({ upper }) => upper))
  const span = maximum - minimum || 1
  const width = 760
  const labelWidth = 210
  const plotWidth = width - labelWidth - 40
  const rowHeight = 34
  const height = 54 + points.length * rowHeight
  const x = (value: number) => labelWidth + ((value - minimum) / span) * plotWidth

  const colorScheme = JOURNAL_COLOR_PRESETS[preset]

  return (
    <section className="adv-result-section" aria-label="Estimated marginal means confidence plot" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '18px', boxShadow: 'var(--shadow-sm)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px', marginBottom: '10px' }}>
        <h3 style={{ margin: 0, color: 'var(--brand-primary)', fontSize: '14px', fontWeight: 700 }}>
          EMM 与置信区间
        </h3>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          点为模型估计边际均值，横线为请求置信水平对应的区间；组间判断应使用 contrast 表。
        </span>

      </div>

      <JournalPresetSelector
        currentPreset={preset}
        onPresetChange={setPreset}
        onExportSvg={() => {
          if (svgRef.current) exportSvgAsFile(svgRef.current, 'emm_confidence_plot.svg')
        }}
        onExport300Dpi={() => {
          if (svgRef.current) exportSvgAs300DpiPng(svgRef.current, 'emm_confidence_plot_300dpi.png')
        }}
      />

      <div className="adv-emm-plot-wrap">
        <svg
          ref={svgRef}
          className="adv-emm-plot"
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${titleId} ${descriptionId}`}
          style={{ width: '100%', aspectRatio: `${width} / ${height}` }}
        >
          <title id={titleId}>Estimated marginal means and confidence intervals</title>
          <desc id={descriptionId}>Model-based marginal means with lower and upper confidence limits. Exact values are available in the adjacent table.</desc>
          <line x1={labelWidth} x2={labelWidth + plotWidth} y1="28" y2="28" stroke="var(--text-muted)" />
          <text x={labelWidth} y="18" textAnchor="start" fill="var(--text-muted)" fontSize="11">{formatAPAStat(minimum)}</text>
          <text x={labelWidth + plotWidth} y="18" textAnchor="end" fill="var(--text-muted)" fontSize="11">{formatAPAStat(maximum)}</text>
          {keyedPoints.map(({ key, point }, index) => {
            const y = 48 + index * rowHeight
            return (
              <g key={key}>
                <text x="4" y={y + 4} fill="var(--text-body)" fontSize="11">{point.label}</text>
                <line x1={x(point.lower)} x2={x(point.upper)} y1={y} y2={y} stroke={colorScheme.line} strokeWidth="2" />
                <line x1={x(point.lower)} x2={x(point.lower)} y1={y - 5} y2={y + 5} stroke={colorScheme.line} />
                <line x1={x(point.upper)} x2={x(point.upper)} y1={y - 5} y2={y + 5} stroke={colorScheme.line} />
                <circle cx={x(point.estimate)} cy={y} r="4.5" fill={colorScheme.line} stroke="var(--bg-surface)">
                  <title>{`${point.label}: ${formatAPAStat(point.estimate)} [${formatAPAStat(point.lower)}, ${formatAPAStat(point.upper)}]`}</title>
                </circle>
              </g>
            )
          })}
        </svg>
      </div>
    </section>
  )
}
