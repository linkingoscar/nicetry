import { memo, useRef, useState, useMemo, useCallback } from 'react'
import { exportSvgAs300DpiPng, exportSvgAsFile } from '../../utils/figureExport'
import { formatAPAStat } from '../../utils/apaFormatter'
import {
  JOURNAL_COLOR_PRESETS,
  type JournalColorPreset,
  JournalPresetSelector,
} from '../shared/JournalPresetSelector'
import { ScreeHoverInfo, type ScreeHoverState } from './ScreeHoverInfo'

interface ScreePlotProps {
  eigenvalues: number[]
  simulatedEigenvalues?: number[]
}

export const ScreePlot = memo(function ScreePlot({ eigenvalues, simulatedEigenvalues }: ScreePlotProps) {
  const [hoverState, setHoverState] = useState<ScreeHoverState | null>(null)
  const [preset, setPreset] = useState<JournalColorPreset>('emerald')
  const svgRef = useRef<SVGSVGElement>(null)

  const width = 520
  const height = 260
  const left = 45
  const right = 20
  const top = 25
  const bottom = 42

  const palette = JOURNAL_COLOR_PRESETS[preset]

  const { sumEigenvalues, points, simulated, pathFn, yMax, yScale } = useMemo(() => {
    const sumEigenvalues = eigenvalues.reduce((acc, curr) => acc + curr, 0)
    const yMax = Math.max(...eigenvalues, ...(simulatedEigenvalues ?? [0])) * 1.15

    const xScale = (index: number) => left + (index / Math.max(1, eigenvalues.length - 1)) * (width - left - right)
    const yScale = (value: number) => height - bottom - (value / Math.max(0.001, yMax)) * (height - top - bottom)

    const points = eigenvalues.map((value, index) => ({
      x: xScale(index),
      y: yScale(value),
      value,
      factor: index + 1,
      varianceExplainedPct: sumEigenvalues > 0 ? (value / sumEigenvalues) * 100 : undefined,
    }))

    const simulated = (simulatedEigenvalues ?? []).map((value, index) => ({
      x: xScale(index),
      y: yScale(value),
      value,
      factor: index + 1,
    }))

    const pathFn = (items: Array<{ x: number; y: number }>) =>
      items.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`).join(' ')

    return { sumEigenvalues, points, simulated, pathFn, yMax, yScale }
  }, [eigenvalues, simulatedEigenvalues])

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * width

    let nearest: ScreeHoverState | null = null
    let minDist = Infinity

    points.forEach((pt, i) => {
      const dist = Math.abs(mouseX - pt.x)
      if (dist < minDist) {
        minDist = dist
        nearest = {
          factor: pt.factor,
          value: pt.value,
          simulatedValue: simulated[i]?.value,
          varianceExplainedPct: pt.varianceExplainedPct,
          cx: pt.x,
          cy: pt.y,
        }
      }
    })

    if (minDist < 40) {
      setHoverState(nearest)
    } else {
      setHoverState(null)
    }
  }, [points, simulated])

  return (
    <div
      style={{
        margin: '16px 0',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '12px',
        padding: '18px',
        boxShadow: 'var(--shadow-sm)',
        position: 'relative',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ margin: 0, color: 'var(--brand-primary)', fontSize: '13px', fontWeight: 700 }}>
          探索性因子分析碎石图 (Scree Plot)
        </h3>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'var(--bg-subtle)', padding: '2px 8px', borderRadius: '999px' }}>
          💡 悬浮数据点查看特征值与方差贡献率
        </span>
      </div>

      <JournalPresetSelector
        currentPreset={preset}
        onPresetChange={setPreset}
        onExportSvg={() => {
          if (svgRef.current) exportSvgAsFile(svgRef.current, 'scree_plot.svg')
        }}
        onExport300Dpi={() => {
          if (svgRef.current) exportSvgAs300DpiPng(svgRef.current, 'scree_plot_300dpi.png')
        }}
      />

      <svg
        ref={svgRef}
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoverState(null)}
        style={{ cursor: 'crosshair', overflow: 'visible', aspectRatio: `${width} / ${height}` }}
        role="img"
        aria-label="探索性因子分析碎石图"
      >
        <title>探索性因子分析碎石图</title>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const value = ratio * yMax
          const y = yScale(value)
          return (
            <g key={ratio}>
              <line x1={left} y1={y} x2={width - right} y2={y} stroke="var(--border-subtle)" />
              <text x={left - 8} y={y + 4} textAnchor="end" fontSize="10" fill="var(--text-muted)">
                {value.toFixed(1)}
              </text>
            </g>
          )
        })}

        {points.map((point) => (
          <g key={point.factor}>
            <line x1={point.x} y1={height - bottom} x2={point.x} y2={height - bottom + 4} stroke="var(--border-subtle)" />
            <text x={point.x} y={height - bottom + 16} textAnchor="middle" fontSize="10" fill="var(--text-muted)">
              {point.factor}
            </text>
          </g>
        ))}

        <line x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} stroke="var(--text-muted)" strokeWidth="1.5" />
        <line x1={left} y1={top} x2={left} y2={height - bottom} stroke="var(--text-muted)" strokeWidth="1.5" />

        <path d={pathFn(points)} fill="none" stroke={palette.line} strokeWidth="2.5" />
        {points.map((point) => (
          <circle
            key={point.factor}
            cx={point.x}
            cy={point.y}
            r={hoverState?.factor === point.factor ? 6 : 4}
            fill={palette.line}
            stroke="var(--bg-surface)"
            strokeWidth="2"
          />
        ))}

        {simulated.length ? (
          <>
            <path d={pathFn(simulated)} fill="none" stroke={palette.minus1sd} strokeWidth="1.5" strokeDasharray="4 3" />
            {simulated.map((point) => (
              <circle key={point.factor} cx={point.x} cy={point.y} r="3" fill={palette.minus1sd} />
            ))}
          </>
        ) : null}

        {/* Hover Indicator Crosshair */}
        {hoverState ? (
          <g style={{ pointerEvents: 'none' }}>
            <line x1={hoverState.cx} y1={top} x2={hoverState.cx} y2={height - bottom} stroke={palette.line} strokeDasharray="3 3" opacity="0.6" />
            <line x1={left} y1={hoverState.cy} x2={width - right} y2={hoverState.cy} stroke={palette.line} strokeDasharray="3 3" opacity="0.6" />
          </g>
        ) : null}
      </svg>

      {/* Floating Hover Info Card */}
      {hoverState ? <ScreeHoverInfo hoverState={hoverState} /> : null}

      <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '10px 0 0' }}>
        提示：实线为观测特征值，红虚线为平行分析模拟 95 百分位阈值。结合 Kaiser 准则（特征值 &gt; 1）和平行分析判断保留因子数。
      </p>

      <details style={{ marginTop: '8px' }}>
        <summary style={{ fontSize: '11px', color: 'var(--text-muted)', cursor: 'pointer' }}>
          查看因子特征值与平行分析明细数据表
        </summary>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse', marginTop: '6px' }}>
          <caption className="sr-only">因子分析特征值与平行分析阈值表</caption>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th scope="col">因子编号</th>
              <th scope="col">观测特征值 (Eigenvalue)</th>
              <th scope="col">平行分析阈值</th>
              <th scope="col">方差解释率 (%)</th>
            </tr>
          </thead>
          <tbody>
            {eigenvalues.map((val, idx) => (
              <tr key={`factor-eigen-${val}`} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td>因子 #{idx + 1}</td>
                <td>{formatAPAStat(val)}</td>
                <td>{simulatedEigenvalues?.[idx] ? formatAPAStat(simulatedEigenvalues[idx]) : '—'}</td>
                <td>{sumEigenvalues > 0 ? `${((val / sumEigenvalues) * 100).toFixed(2)}%` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
})
