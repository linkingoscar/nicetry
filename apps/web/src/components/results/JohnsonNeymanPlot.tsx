import { memo, useRef, useState, useMemo, useCallback } from 'react'
import type { JohnsonNeymanResult } from '../../types/models'
import { exportSvgAs300DpiPng, exportSvgAsFile } from '../../utils/figureExport'
import {
  JOURNAL_COLOR_PRESETS,
  type JournalColorPreset,
  JournalPresetSelector,
} from '../shared/JournalPresetSelector'
import {
  buildJNGeometry,
  JN_REGION_LABELS,
  nearestJNHover,
} from './johnsonNeymanGeometry'

interface JohnsonNeymanPlotProps {
  predictorLabel: string
  moderatorLabel: string
  result: JohnsonNeymanResult
}

export const JohnsonNeymanPlot = memo(function JohnsonNeymanPlot({
  predictorLabel,
  moderatorLabel,
  result,
}: JohnsonNeymanPlotProps) {
  const [hoverState, setHoverState] = useState<ReturnType<typeof nearestJNHover>>(null)
  const [preset, setPreset] = useState<JournalColorPreset>('emerald')
  const svgRef = useRef<SVGSVGElement>(null)

  const grid = result.grid ?? []
  const palette = JOURNAL_COLOR_PRESETS[preset]

  const width = 560
  const height = 280
  const left = 58
  const right = 22
  const top = 22
  const bottom = 42

  const geometry = useMemo(
    () => buildJNGeometry(result, grid, width, height, left, right, top, bottom),
    [grid, result],
  )

  const handleMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if (!geometry) return
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = ((e.clientX - rect.left) / rect.width) * width
    setHoverState(nearestJNHover(geometry, grid, mouseX))
  }, [geometry, grid])

  if (!grid.length || !geometry) return null

  const statusColor = (status: 'positive' | 'negative' | 'not_significant') => {
    if (status === 'positive') return palette.positive
    if (status === 'negative') return palette.negative
    return 'var(--text-muted)'
  }

  return (
    <div style={{ margin: '16px 0', background: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: '12px', padding: '18px', boxShadow: 'var(--shadow-sm)', position: 'relative' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
        <h3 style={{ margin: 0, color: 'var(--brand-primary)', fontSize: '13px', fontWeight: 700 }}>
          Johnson–Neyman 条件效应图：{predictorLabel} × {moderatorLabel}
        </h3>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', background: 'var(--bg-subtle)', padding: '2px 8px', borderRadius: '999px' }}>
          💡 沿曲线滑动鼠标可查看条件效应与 95% CI
        </span>
      </div>

      <JournalPresetSelector
        currentPreset={preset}
        onPresetChange={setPreset}
        onExportSvg={() => {
          if (svgRef.current) exportSvgAsFile(svgRef.current, 'johnson_neyman_plot.svg')
        }}
        onExport300Dpi={() => {
          if (svgRef.current) exportSvgAs300DpiPng(svgRef.current, 'johnson_neyman_plot_300dpi.png')
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
        aria-label={`Johnson-Neyman 条件效应图: ${predictorLabel} 与 ${moderatorLabel}`}
      >
        <title>{`${predictorLabel} 对结果的条件效应随 ${moderatorLabel} 的变化`}</title>
        <line x1={left} y1={geometry.yScale(0)} x2={width - right} y2={geometry.yScale(0)} stroke="var(--text-caption)" strokeDasharray="4 4" />
        
        {(result.observedBoundaries ?? []).map((boundary) => (
          <g key={boundary}>
            <line x1={geometry.xScale(boundary)} y1={top} x2={geometry.xScale(boundary)} y2={height - bottom} stroke="#b45309" strokeDasharray="3 3" strokeWidth="1.5" />
            <text x={geometry.xScale(boundary)} y={top - 4} textAnchor="middle" fontSize="9" fill="#b45309" fontWeight="bold">
              J-N 临界点: {boundary.toFixed(2)}
            </text>
          </g>
        ))}

        <polyline points={geometry.lowerPoints} fill="none" stroke="var(--border-subtle)" strokeWidth="1.2" strokeDasharray="3 3" />
        <polyline points={geometry.upperPoints} fill="none" stroke="var(--border-subtle)" strokeWidth="1.2" strokeDasharray="3 3" />
        <polyline points={geometry.effectPoints} fill="none" stroke="var(--brand-primary)" strokeWidth="2.8" />
        <line x1={left} y1={height - bottom} x2={width - right} y2={height - bottom} stroke="var(--text-muted)" />
        <line x1={left} y1={top} x2={left} y2={height - bottom} stroke="var(--text-muted)" />
        <text x={(left + width - right) / 2} y={height - 10} textAnchor="middle" fontSize="11" fill="var(--text-body)">{moderatorLabel}</text>
        <text x={14} y={(top + height - bottom) / 2} textAnchor="middle" fontSize="11" fill="var(--text-body)" transform={`rotate(-90 14 ${(top + height - bottom) / 2})`}>条件效应</text>

        {/* Hover Crosshairs & Data Marker */}
        {hoverState ? (
          <g style={{ pointerEvents: 'none' }}>
            <line x1={hoverState.cx} y1={top} x2={hoverState.cx} y2={height - bottom} stroke="var(--brand-primary)" strokeDasharray="3 3" opacity="0.6" />
            <line x1={left} y1={hoverState.cy} x2={width - right} y2={hoverState.cy} stroke="var(--brand-primary)" strokeDasharray="3 3" opacity="0.6" />
            <circle cx={hoverState.cx} cy={hoverState.cy} r="6" fill={statusColor(hoverState.status)} stroke="var(--bg-surface)" strokeWidth="2" />
          </g>
        ) : null}
      </svg>

      {/* Hover Info Tooltip Popover */}
      {hoverState ? (
        <div
          className="glass-panel"
          style={{
            position: 'absolute',
            top: '40px',
            right: '24px',
            background: 'rgba(15, 23, 42, 0.88)',
            backdropFilter: 'blur(10px)',
            WebkitBackdropFilter: 'blur(10px)',
            border: '1px solid rgba(255, 255, 255, 0.16)',
            color: '#ffffff',
            padding: '10px 14px',
            borderRadius: '10px',
            fontSize: '11px',
            boxShadow: 'var(--shadow-hover)',
            zIndex: 10,
            display: 'grid',
            gap: '3px',
            pointerEvents: 'none',
            transition: 'opacity 0.15s var(--ease-out-spring), transform 0.15s var(--ease-out-spring)',
          }}
        >
          <div style={{ color: '#38bdf8', fontWeight: 700 }}>
            {moderatorLabel} = {hoverState.moderatorValue.toFixed(3)}
          </div>
          <div>条件效应: <strong style={{ color: '#4a6dde' }}>{hoverState.effect.toFixed(3)}</strong></div>
          <div style={{ color: '#cbd5e1' }}>95% CI: [{hoverState.lower.toFixed(3)}, {hoverState.upper.toFixed(3)}]</div>
          <div>
            判定状态:{' '}
            <span style={{ color: statusColor(hoverState.status), fontWeight: 700 }}>
              {JN_REGION_LABELS[hoverState.status]}
            </span>
          </div>
        </div>
      ) : null}

      <p className="method-note" style={{ marginTop: '10px', fontSize: '11px', color: 'var(--text-muted)' }}>
        深绿实线为条件效应，灰虚线为 {(result.confidenceLevel ?? 0.95) * 100}% CI，琥珀色虚线为 J-N 临界点。
        {(result.regions ?? []).map((region) => ` [${region.lower.toFixed(2)}, ${region.upper.toFixed(2)}] ${JN_REGION_LABELS[region.status]}`).join('；')}
      </p>

      <details style={{ marginTop: '8px' }}>
        <summary style={{ fontSize: '11px', color: 'var(--text-muted)', cursor: 'pointer' }}>
          查看 Johnson-Neyman 调节条件效应明细表格数据
        </summary>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse', marginTop: '6px' }}>
          <caption className="sr-only">Johnson-Neyman 条件效应网格表</caption>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th scope="col">{moderatorLabel} 取值</th>
              <th scope="col">{predictorLabel} 条件效应 (b)</th>
              <th scope="col">95% CI 下限</th>
              <th scope="col">95% CI 上限</th>
              <th scope="col">显著性状态</th>
            </tr>
          </thead>
          <tbody>
            {grid.map((row) => (
              <tr key={`jn-row-${row.moderatorValue.toFixed(4)}-${row.effect.toFixed(4)}`} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td>{row.moderatorValue.toFixed(3)}</td>
                <td>{row.effect.toFixed(3)}</td>
                <td>{row.lower.toFixed(3)}</td>
                <td>{row.upper.toFixed(3)}</td>
                <td>{row.significant ? (row.effect >= 0 ? '显著正向' : '显著负向') : '不显著'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </div>
  )
})
