import type React from 'react'
import { memo, useState } from 'react'
import {
  formatAPAConfidenceInterval,
  formatAPAPValue,
  formatAPASigStars,
  formatAPAStat,
} from '../../utils/apaFormatter'
import { getScientificCellColor, type HeatmapPalette } from './correlationHeatmapColor'
import { CorrelationHeatmapAccessibleTable } from './CorrelationHeatmapAccessibleTable'
import styles from './CorrelationHeatmap.module.css'

export type { HeatmapPalette }

interface CorrelationHeatmapProps {
  confidenceLevel?: number
  variables: Array<{ id: string; label: string }>
  coefficients: Array<Array<number | null>>
  pValues?: Array<Array<number | null>>
  counts?: Array<Array<number | null>>
  ciLower?: Array<Array<number | null>>
  ciUpper?: Array<Array<number | null>>
  palette?: HeatmapPalette
}

export const CorrelationHeatmap = memo(function CorrelationHeatmap({
  variables,
  coefficients,
  pValues = [],
  counts = [],
  ciLower = [],
  ciUpper = [],
  palette = 'okabe_ito',
  confidenceLevel = 0.95,
}: CorrelationHeatmapProps) {
  const [hoverCell, setHoverCell] = useState<{ row: number; col: number } | null>(null)
  const [currentPalette, setCurrentPalette] = useState<HeatmapPalette>(palette)

  const cellSize = Math.min(48, Math.max(32, Math.floor(450 / variables.length)))
  const left = 140
  const top = 50

  const handleMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const mouseY = e.clientY - rect.top

    const col = Math.floor((mouseX - left) / cellSize)
    const row = Math.floor((mouseY - top) / cellSize)

    if (row >= 0 && row < variables.length && col >= 0 && col <= row) {
      setHoverCell({ row, col })
    } else {
      setHoverCell(null)
    }
  }

  const activeCellData = hoverCell
    ? {
        rowVar: variables[hoverCell.row],
        colVar: variables[hoverCell.col],
        r: coefficients[hoverCell.row]?.[hoverCell.col],
        p: hoverCell.row === hoverCell.col ? null : pValues[hoverCell.row]?.[hoverCell.col],
        n: counts[hoverCell.row]?.[hoverCell.col],
        lower: ciLower[hoverCell.row]?.[hoverCell.col],
        upper: ciUpper[hoverCell.row]?.[hoverCell.col],
      }
    : null

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <h3 className={styles.heading}>
          <span>🎨 相关系数热力图 (Interactive Cell Inspector)</span>
        </h3>

        <div className={styles.toolbar}>
          <div className={styles.paletteGroup}>
            <span className={styles.paletteLabel}>色板:</span>
            <button
              type="button"
              onClick={() => setCurrentPalette('okabe_ito')}
              className={styles.paletteButton}
              style={{
                border: `1px solid ${currentPalette === 'okabe_ito' ? 'var(--brand-accent)' : 'var(--border-subtle)'}`,
                background: currentPalette === 'okabe_ito' ? 'var(--bg-hover)' : 'var(--bg-surface)',
                color: 'var(--text-main)',
                fontWeight: currentPalette === 'okabe_ito' ? 700 : 400,
              }}
            >
              Okabe-Ito (色盲安全)
            </button>
            <button
              type="button"
              onClick={() => setCurrentPalette('viridis')}
              className={styles.paletteButton}
              style={{
                border: `1px solid ${currentPalette === 'viridis' ? 'var(--brand-accent)' : 'var(--border-subtle)'}`,
                background: currentPalette === 'viridis' ? 'var(--bg-hover)' : 'var(--bg-surface)',
                color: 'var(--text-main)',
                fontWeight: currentPalette === 'viridis' ? 700 : 400,
              }}
            >
              Viridis
            </button>
          </div>

          <div className={styles.legendGroup}>
            <span className={styles.legendItem}>
              <span className={styles.legendSwatch} style={{ background: getScientificCellColor(1, currentPalette) }} />
              正相关 (<em>r</em> &gt; 0)
            </span>
            <span className={styles.legendItem}>
              <span className={styles.legendSwatch} style={{ background: getScientificCellColor(-1, currentPalette) }} />
              负相关 (<em>r</em> &lt; 0)
            </span>
          </div>
        </div>
      </div>

      <div className={styles.plotContainer}>
        <svg
          width={left + variables.length * cellSize + 30}
          height={top + variables.length * cellSize + 30}
          onMouseMove={handleMouseMove}
          onMouseLeave={() => setHoverCell(null)}
          style={{ cursor: hoverCell ? 'pointer' : 'default', aspectRatio: `${left + variables.length * cellSize + 30} / ${top + variables.length * cellSize + 30}` }}
          role="img"
          aria-label="相关系数热力矩阵图"
        >
          <title>相关系数热力图</title>
          {/* Column Header Indexes */}
          {variables.map((variable, index) => {
            const isColHovered = hoverCell?.col === index
            return (
              <text
                key={variable.id}
                x={left + index * cellSize + cellSize / 2}
                y={top - 12}
                textAnchor="middle"
                fontSize="11"
                fontWeight={isColHovered ? 'bold' : 'normal'}
                fill={isColHovered ? 'var(--brand-accent)' : 'var(--text-muted)'}
              >
                {index + 1}
              </text>
            )
          })}

          {/* Rows & Cells */}
          {variables.map((rowVariable, row) => {
            const isRowHovered = hoverCell?.row === row
            return (
              <g key={rowVariable.id}>
                {/* Row Header Label */}
                <text
                  x={left - 12}
                  y={top + row * cellSize + cellSize / 2 + 4}
                  textAnchor="end"
                  fontSize="11"
                  fontWeight={isRowHovered ? 'bold' : 'normal'}
                  fill={isRowHovered ? 'var(--brand-accent)' : 'var(--text-body)'}
                >
                  {row + 1}. {rowVariable.label.length > 9 ? `${rowVariable.label.slice(0, 8)}...` : rowVariable.label}
                </text>

                {coefficients[row]?.map((value, column) => {
                  if (column > row) return null
                  const isCellHovered = hoverCell?.row === row && hoverCell?.col === column
                  const isRowOrColHovered = hoverCell?.row === row || hoverCell?.col === column

                  return (
                    <g
                      key={variables[column].id}
                      aria-label={`${rowVariable.label} 与 ${variables[column].label} 的相关系数为 ${formatAPAStat(value)}`}
                    >

                      <rect
                        x={left + column * cellSize}
                        y={top + row * cellSize}
                        width={cellSize - 2}
                        height={cellSize - 2}
                        rx="4"
                        fill={getScientificCellColor(value, currentPalette)}
                        stroke={isCellHovered ? 'var(--text-main)' : isRowOrColHovered ? 'var(--brand-accent)' : 'transparent'}
                        strokeWidth={isCellHovered ? 2 : isRowOrColHovered ? 1.5 : 0}
                        style={{ transition: 'all 0.15s ease' }}
                      />
                      <text
                        x={left + column * cellSize + cellSize / 2}
                        y={top + row * cellSize + cellSize / 2 + 4}
                        textAnchor="middle"
                        fontSize="10"
                        fontWeight={isCellHovered ? 'bold' : '500'}
                        fill={value !== null && Math.abs(value) > 0.35 ? '#ffffff' : 'var(--text-main)'}
                        pointerEvents="none"
                      >
                        {value === null ? '—' : formatAPAStat(value, 2)}
                      </text>
                    </g>
                  )
                })}
              </g>
            )
          })}
        </svg>

        {/* Floating Cell Inspector Tooltip Card */}
        {activeCellData && hoverCell ? (
          <div
            className={`glass-panel ${styles.tooltip}`}
            style={{
              top: `${top + hoverCell.row * cellSize - 10}px`,
              left: `${left + hoverCell.col * cellSize + cellSize + 15}px`,
            }}
          >
            <div className={styles.tooltipTitle}>
              {activeCellData.colVar.label} × {activeCellData.rowVar.label}
            </div>
            <div>
              相关系数 (<em>r</em>):{' '}
              <strong className={styles.tooltipR}>
                {formatAPAStat(activeCellData.r)}
                {formatAPASigStars(activeCellData.p)}
              </strong>
            </div>
            {typeof activeCellData.p === 'number' ? (
              <div><em>p</em> 值: {formatAPAPValue(activeCellData.p)}</div>
            ) : null}
            {typeof activeCellData.n === 'number' ? <div>样本数 (<em>N</em>): {activeCellData.n}</div> : null}
            {typeof activeCellData.lower === 'number' && typeof activeCellData.upper === 'number' ? (
              <div className={styles.tooltipCi}>
                {formatAPAConfidenceInterval(activeCellData.lower, activeCellData.upper, 3, confidenceLevel)}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* Accessible Tabular Alternative for Screen Readers */}
      <CorrelationHeatmapAccessibleTable
        variables={variables}
        coefficients={coefficients}
        pValues={pValues}
      />
    </div>
  )
})
