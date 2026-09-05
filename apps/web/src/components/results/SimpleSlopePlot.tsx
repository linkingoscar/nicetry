import { memo, useRef, useState, useMemo, useCallback } from 'react'
import type { ResultBundle } from '../../types'
import { exportSvgAs300DpiPng, exportSvgAsFile } from '../../utils/figureExport'
import {
  JOURNAL_COLOR_PRESETS,
  type JournalColorPreset,
  JournalPresetSelector,
} from '../shared/JournalPresetSelector'

type ModerationPlot = NonNullable<ResultBundle['moderationPlots']>[number]

interface HoverState {
  lineLabel: string
  moderatorValue: number
  xValue: number
  predictedValue: number
  cx: number
  cy: number
  color: string
}

export const SimpleSlopePlot = memo(function SimpleSlopePlot({ plot }: { plot: ModerationPlot }) {
  const [hoverState, setHoverState] = useState<HoverState | null>(null)
  const [preset, setPreset] = useState<JournalColorPreset>('emerald')
  const svgRef = useRef<SVGSVGElement>(null)

  const width = 480
  const height = 260
  const left = 50
  const right = 20
  const top = 25
  const bottom = 40

  const currentPalette = JOURNAL_COLOR_PRESETS[preset]
  const colors: Record<string, string> = useMemo(() => ({
    percentile_16: currentPalette.minus1sd,
    median: currentPalette.mean,
    percentile_84: currentPalette.plus1sd,
    mean_minus_1sd: currentPalette.minus1sd,
    mean: currentPalette.mean,
    mean_plus_1sd: currentPalette.plus1sd,
  }), [currentPalette])

  const geometry = useMemo(() => {
    if (!plot?.lines?.length) return null
    const allX = plot.lines.flatMap((line) => line.xValues)
    const allY = plot.lines.flatMap((line) => [...line.predictedValues, ...(line.confidenceLower ?? []), ...(line.confidenceUpper ?? [])])
    const xMin = Math.min(...allX)
    const xMax = Math.max(...allX)
    const yMin = Math.min(...allY)
    const yMax = Math.max(...allY)
    const padding = Math.max(Number.EPSILON, yMax - yMin) * 0.15
    const chartMin = yMin - padding
    const chartMax = yMax + padding

    const xScale = (value: number) => left + ((value - xMin) / Math.max(Number.EPSILON, xMax - xMin)) * (width - left - right)
    const yScale = (value: number) => height - bottom - ((value - chartMin) / Math.max(Number.EPSILON, chartMax - chartMin)) * (height - top - bottom)

    return { xScale, yScale, chartMin, chartMax, xMin, xMax }
  }, [plot])

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!geometry) return
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * width

    let nearest: HoverState | null = null
    let minDist = Infinity

    for (const line of plot.lines) {
      const key = Object.keys(colors).find((candidate) => line.label.includes(candidate)) ?? 'mean'
      const color = colors[key]
      for (let i = 0; i < line.xValues.length; i++) {
        const cx = geometry.xScale(line.xValues[i])
        const dist = Math.abs(cx - mouseX)
        if (dist < minDist && dist < 30) {
          minDist = dist
          nearest = {
            lineLabel: line.label,
            moderatorValue: line.moderatorValue,
            xValue: line.xValues[i],
            predictedValue: line.predictedValues[i],
            cx,
            cy: geometry.yScale(line.predictedValues[i]),
            color,
          }
        }
      }
    }

    if (minDist < 30) {
      setHoverState(nearest)
    } else {
      setHoverState(null)
    }
  }, [colors, geometry, plot.lines])

  return (
    <div className="simple-slope-plot-container" style={{ position: 'relative', marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <JournalPresetSelector currentPreset={preset} onPresetChange={setPreset} />
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="secondary-button"
            style={{ fontSize: '11px', padding: '3px 8px' }}
            onClick={() => svgRef.current && exportSvgAsFile(svgRef.current, `simple-slope-${plot.id}.svg`)}
          >
            导出 SVG
          </button>
          <button
            type="button"
            className="secondary-button"
            style={{ fontSize: '11px', padding: '3px 8px' }}
            onClick={() => svgRef.current && exportSvgAs300DpiPng(svgRef.current, `simple-slope-${plot.id}.png`)}
          >
            导出高清 PNG (300 DPI)
          </button>
        </div>
      </div>

      <svg
        ref={svgRef}
        role="img"
        aria-label="简单斜率检验图"
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: '100%', height: 'auto', background: 'var(--bg-surface, #ffffff)', borderRadius: '8px', border: '1px solid var(--border-subtle, #e2e8f0)' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverState(null)}
      >
        {/* Y Axis Grid Lines */}
        {geometry ? [0, 0.25, 0.5, 0.75, 1].map((pct) => {
          const yVal = geometry.chartMin + pct * (geometry.chartMax - geometry.chartMin)
          const yPos = geometry.yScale(yVal)
          return (
            <g key={pct}>
              <line x1={left} y1={yPos} x2={width - right} y2={yPos} stroke="var(--border-subtle, #e2e8f0)" strokeDasharray="3 3" opacity={0.6} />
              <text x={left - 6} y={yPos + 4} textAnchor="end" fontSize="10" fill="var(--text-muted, #566579)">
                {yVal.toFixed(2)}
              </text>
            </g>
          )
        }) : null}

        {/* X Axis Ticks */}
        {geometry && plot.lines[0]?.xValues.map((xVal) => (
          <text key={xVal} x={geometry.xScale(xVal)} y={height - bottom + 16} textAnchor="middle" fontSize="10" fill="var(--text-muted, #566579)">
            {xVal.toFixed(2)}
          </text>
        ))}

        {/* Axis Labels */}
        <text x={(left + width - right) / 2} y={height - 6} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--text-main, #0f172a)">
          {plot.predictorLabel} (X)
        </text>
        <text
          x={14}
          y={(top + height - bottom) / 2}
          textAnchor="middle"
          fontSize="11"
          fontWeight="600"
          fill="var(--text-main, #0f172a)"
          transform={`rotate(-90 14 ${(top + height - bottom) / 2})`}
        >
          {plot.outcomeLabel} (Y)
        </text>

        {/* Confidence Bands & Trend Lines */}
        {geometry && plot.lines.map((line) => {
          const key = Object.keys(colors).find((candidate) => line.label.includes(candidate)) ?? 'mean'
          const color = colors[key]
          const points = line.xValues.map((x, i) => `${geometry.xScale(x)},${geometry.yScale(line.predictedValues[i])}`).join(' ')

          // Construct CI polygon points if available
          let bandPoints = ''
          const lower = line.confidenceLower
          const upper = line.confidenceUpper
          if (lower && upper && lower.length === line.xValues.length && upper.length === line.xValues.length) {
            const upperPoints = line.xValues.map((x, i) => `${geometry.xScale(x)},${geometry.yScale(upper[i])}`)
            const lowerPoints = line.xValues.map((x, i) => `${geometry.xScale(x)},${geometry.yScale(lower[i])}`).reverse()
            bandPoints = [...upperPoints, ...lowerPoints].join(' ')
          }

          return (
            <g key={line.label}>
              {bandPoints ? <polygon points={bandPoints} fill={color} opacity={0.12} /> : null}
              <polyline points={points} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" />
              {line.xValues.map((x, i) => (
                <circle key={x} cx={geometry.xScale(x)} cy={geometry.yScale(line.predictedValues[i])} r="4" fill={color} stroke="var(--bg-surface, #ffffff)" strokeWidth="1.5" />
              ))}
            </g>
          )
        })}

        {/* Hover Crosshair & Dot */}
        {hoverState ? (
          <g>
            <line x1={hoverState.cx} y1={top} x2={hoverState.cx} y2={height - bottom} stroke="var(--text-muted, #566579)" strokeDasharray="2 2" opacity={0.5} />
            <circle cx={hoverState.cx} cy={hoverState.cy} r="6" fill={hoverState.color} stroke="#ffffff" strokeWidth="2" />
          </g>
        ) : null}

        {/* Legend Header */}
        <g transform={`translate(${left + 10}, ${top + 10})`}>
          {plot.lines.map((line, idx) => {
            const key = Object.keys(colors).find((candidate) => line.label.includes(candidate)) ?? 'mean'
            const color = colors[key]
            return (
              <g key={line.label} transform={`translate(${idx * 135}, 0)`}>
                <rect width="12" height="12" rx="2" fill={color} />
                <text x="16" y="10" fontSize="10" fill="var(--text-main, #0f172a)">
                  {line.label} ({line.moderatorValue.toFixed(2)})
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Interactive Tooltip Card */}
      {hoverState ? (
        <div
          style={{
            position: 'absolute',
            left: `${(hoverState.cx / width) * 100}%`,
            top: `${(hoverState.cy / height) * 100}%`,
            transform: 'translate(-50%, -120%)',
            background: 'rgba(15, 23, 42, 0.92)',
            color: '#ffffff',
            padding: '6px 10px',
            borderRadius: '6px',
            fontSize: '11px',
            pointerEvents: 'none',
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            whiteSpace: 'nowrap',
            zIndex: 10,
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: '2px', color: hoverState.color }}>{hoverState.lineLabel}</div>
          <div>{plot.predictorLabel}: {hoverState.xValue.toFixed(3)}</div>
          <div>预测响应值: <strong style={{ color: '#4a6dde' }}>{hoverState.predictedValue.toFixed(3)}</strong></div>
        </div>
      ) : null}

      <p style={{ fontSize: '11px', color: 'var(--text-muted, #566579)', margin: '8px 0 0' }}>
        横轴为 {plot.predictorLabel}；纵轴为{plot.outcomeScale === 'probability' ? '预测概率' : `${plot.outcomeLabel} 的模型预测值`}，淡色区域为 95% 置信带。
      </p>
    </div>
  )
})
