import { memo, useRef, useState, useMemo } from 'react'
import type { InvarianceResult } from '../../types'
import { formatAPAConfidenceInterval, formatAPAStat } from '../../utils/apaFormatter'
import { exportSvgAs300DpiPng, exportSvgAsFile } from '../../utils/figureExport'
import {
  JOURNAL_COLOR_PRESETS,
  type JournalColorPreset,
  JournalPresetSelector,
} from '../shared/JournalPresetSelector'

type GroupParameter = NonNullable<InvarianceResult['groupParameters']>[number]

export const PathCoefficientForestPlot = memo(function PathCoefficientForestPlot({
  groups,
}: {
  groups: GroupParameter[]
}) {
  const [preset, setPreset] = useState<JournalColorPreset>('emerald')
  const svgRef = useRef<SVGSVGElement>(null)

  const palette = JOURNAL_COLOR_PRESETS[preset]
  const groupColors = useMemo(
    () => [palette.mean, palette.plus1sd, palette.minus1sd, '#8b5cf6', '#ec4899'],
    [palette]
  )

  const { rows, groupNames, pathKeys, xScale, width, rowHeight, left, right, top, height } = useMemo(() => {
    const pathKeys = Array.from(
      new Set(groups.flatMap((group) => group.paths.map((path) => `${path.from}\r${path.to}`))),
    )

    const rows = pathKeys.flatMap((key) => {
      const [from, to] = key.split('\r')
      return groups.flatMap((group) => {
        const match = group.paths.find((path) => path.from === from && path.to === to)
        if (!match) return []

        const ciLower =
          typeof match.ciLower === 'number' && Number.isFinite(match.ciLower)
            ? match.ciLower
            : null
        const ciUpper =
          typeof match.ciUpper === 'number' && Number.isFinite(match.ciUpper)
            ? match.ciUpper
            : null
        const hasConfidenceInterval = ciLower !== null && ciUpper !== null && ciLower <= ciUpper

        return [{
          key: `${group.group}:${key}`,
          group: group.group,
          label: `${from} → ${to}`,
          estimate: match.estimate,
          se: match.standardError,
          pValue: match.pValue,
          stdAll: match.stdAll,
          ciLower: hasConfidenceInterval ? ciLower : null,
          ciUpper: hasConfidenceInterval ? ciUpper : null,
        }]
      })
    })

    const groupNames = Array.from(new Set(groups.map((group) => group.group)))

    const values = rows.flatMap((row) => [
      row.estimate,
      ...(row.ciLower === null ? [] : [row.ciLower]),
      ...(row.ciUpper === null ? [] : [row.ciUpper]),
    ])
    const minVal = Math.min(0, ...values)
    const maxVal = Math.max(0, ...values)
    const pad = Math.max(0.1, (maxVal - minVal) * 0.15)
    const domainMin = minVal - pad
    const domainMax = maxVal - pad < domainMin ? domainMin + 1 : maxVal + pad

    const width = 640
    const rowHeight = 28
    const left = 210
    const right = 20
    const top = 40
    const height = top + pathKeys.length * groupNames.length * rowHeight + 50

    const xScale = (val: number) =>
      left + ((val - domainMin) / (domainMax - domainMin)) * (width - left - right)

    return { rows, groupNames, pathKeys, xScale, width, rowHeight, left, right, top, height }
  }, [groups])

  if (rows.length === 0) return null

  return (
    <figure className="forest-plot-card" style={{ marginTop: '16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <figcaption className="eyebrow" style={{ margin: 0 }}>跨组路径系数森林图</figcaption>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <JournalPresetSelector currentPreset={preset} onPresetChange={setPreset} />
          <button
            type="button"
            className="secondary-button"
            style={{ fontSize: '11px', padding: '3px 8px' }}
            onClick={() => svgRef.current && exportSvgAsFile(svgRef.current, 'path-forest-plot.svg')}
          >
            导出 SVG
          </button>
          <button
            type="button"
            className="secondary-button"
            style={{ fontSize: '11px', padding: '3px 8px' }}
            onClick={() => svgRef.current && exportSvgAs300DpiPng(svgRef.current, 'path-forest-plot.png')}
          >
            导出 PNG (300 DPI)
          </button>
        </div>
      </div>
      <svg ref={svgRef} viewBox={`0 0 ${width} ${height}`} className="forest-plot-svg" role="img" aria-label="各组结构路径系数森林图">
        <line x1={xScale(0)} x2={xScale(0)} y1={top - 10} y2={height - 40} stroke="var(--border-subtle)" strokeDasharray="3 3" />
        {pathKeys.map((key: string, pathIdx: number) => {
          const [from, to] = key.split('\r')
          const pathRows = rows.filter((r) => r.label === `${from} → ${to}`)
          const startY = top + pathIdx * groupNames.length * rowHeight

          return (
            <g key={key}>
              <text x="10" y={startY + 16} fill="var(--text-main)" fontSize="12" fontWeight="700">
                {from} → {to}
              </text>
              {pathRows.map((row) => {
                const groupIndex = groupNames.indexOf(row.group)
                const y = startY + groupIndex * rowHeight + 14
                const color = groupColors[groupIndex % groupColors.length]

                return (
                  <g key={row.key}>
                    <text x="24" y={y + 4} fill="var(--text-muted)" fontSize="11">
                      {row.group}
                    </text>
                    {row.ciLower !== null && row.ciUpper !== null && (
                      <line
                        x1={xScale(row.ciLower)}
                        x2={xScale(row.ciUpper)}
                        y1={y}
                        y2={y}
                        stroke={color}
                        strokeWidth="2"
                      />
                    )}
                    <circle cx={xScale(row.estimate)} cy={y} r="4" fill={color} />
                    <text x={width - right} y={y + 4} fill="var(--text-body)" fontSize="10" textAnchor="end" fontFamily="monospace">
                      B={formatAPAStat(row.estimate)} p={formatAPAStat(row.pValue)} (β={formatAPAStat(row.stdAll)})
                    </text>
                  </g>
                )
              })}
            </g>
          )
        })}
        <line x1={left} x2={width - right} y1={height - 34} y2={height - 34} stroke="var(--border-subtle)" />
        <text x={(left + width - right) / 2} y={height - 10} fill="var(--text-body)" fontSize="11" textAnchor="middle">
          未标准化 B
        </text>
      </svg>

      <details style={{ marginTop: '8px' }}>
        <summary style={{ fontSize: '11px', color: 'var(--text-muted)', cursor: 'pointer' }}>
          查看路径系数与置信区间全量数据表
        </summary>
        <table style={{ width: '100%', fontSize: '11px', borderCollapse: 'collapse', marginTop: '6px' }}>
          <caption className="sr-only">路径系数森林图数据明细表</caption>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
              <th scope="col">路径关系</th>
              <th scope="col">分组/类型</th>
              <th scope="col">点估计值 B (未标准化)</th>
              <th scope="col">标准误 (SE)</th>
              <th scope="col">95% 置信区间</th>
              <th scope="col">p 值</th>
              <th scope="col">标准化 β</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => (
              <tr key={`${row.key ?? idx}`} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                <td>{row.label}</td>
                <td>{row.group ?? '全样本'}</td>
                <td>{formatAPAStat(row.estimate)}</td>
                <td>{formatAPAStat(row.se)}</td>
                <td>{formatAPAConfidenceInterval(row.ciLower, row.ciUpper)}</td>
                <td>{formatAPAStat(row.pValue)}</td>
                <td>{formatAPAStat(row.stdAll)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  )
})
