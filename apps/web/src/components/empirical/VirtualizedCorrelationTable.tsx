import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'

interface VirtualizedCorrelationTableProps {
  confidenceLevel?: number
  variables: Array<{ id: string; label: string }>
  coefficients: Array<Array<number | null>>
  pValues: Array<Array<number | null>>
  counts: Array<Array<number>>
  ciLower: Array<Array<number | null>>
  ciUpper: Array<Array<number | null>>
  metric: (v: number | null | undefined) => string
  significance: (v: number | null | undefined) => string
}

export function VirtualizedCorrelationTable({
  variables,
  coefficients,
  pValues,
  counts,
  ciLower,
  ciUpper,
  metric,
  significance,
  confidenceLevel = 0.95,
}: VirtualizedCorrelationTableProps) {
  const parentRef = useRef<HTMLDivElement>(null)

  // Row 0 is the header, rows 1..N are variables
  const rowVirtualizer = useVirtualizer({
    count: variables.length + 1,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => (index === 0 ? 45 : 38),
    overscan: 5,
  })

  // Column 0 is row labels, columns 1..N are data cells
  const columnVirtualizer = useVirtualizer({
    count: variables.length + 1,
    getScrollElement: () => parentRef.current,
    estimateSize: (index) => (index === 0 ? 180 : 75),
    horizontal: true,
    overscan: 5,
  })

  const virtualRows = rowVirtualizer.getVirtualItems()
  const virtualCols = columnVirtualizer.getVirtualItems()

  return (
    // biome-ignore lint/a11y/useSemanticElements: two-axis virtualization requires positioned non-table elements.
    <div
      ref={parentRef}
      role="table"
      aria-label="相关矩阵"
      aria-rowcount={variables.length + 1}
      aria-colcount={variables.length + 1}
      className="virtualized-table-container"
      style={{
        overflow: 'auto',
        maxHeight: '500px',
        maxWidth: '100%',
        border: '1px solid #d1d5db',
        borderRadius: '8px',
        background: '#fff',
        position: 'relative',
      }}
    >
      <div
        style={{
          height: `${rowVirtualizer.getTotalSize()}px`,
          width: `${columnVirtualizer.getTotalSize()}px`,
          position: 'relative',
        }}
      >
        {virtualRows.map((virtualRow) => {
          const rowIndex = virtualRow.index
          return virtualCols.map((virtualCol) => {
            const colIndex = virtualCol.index

            // Header row cell
            if (rowIndex === 0) {
              return (
                // biome-ignore lint/a11y/useSemanticElements: virtualized headers cannot use native table layout.
                <div
                  key={`header-${colIndex}`}
                  role="columnheader"
                  tabIndex={-1}
                  aria-rowindex={1}
                  aria-colindex={colIndex + 1}
                  style={{
                    position: colIndex === 0 ? 'sticky' : 'absolute',
                    top: 0,
                    left: colIndex === 0 ? 0 : `${virtualCol.start}px`,
                    width: `${virtualCol.size}px`,
                    height: `${virtualRow.size}px`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: colIndex === 0 ? 'flex-start' : 'center',
                    padding: '8px',
                    fontWeight: 'bold',
                    background: '#f3f4f6',
                    borderBottom: '2px solid #d1d5db',
                    borderRight: colIndex === variables.length ? 'none' : '1px solid #e5e7eb',
                    fontSize: '13px',
                    color: '#374151',
                    zIndex: colIndex === 0 ? 3 : 2,
                  }}
                >
                  {colIndex === 0 ? '变量' : colIndex}
                </div>
              )
            }

            // Column 0 is the row label
            if (colIndex === 0) {
              return (
                // biome-ignore lint/a11y/useSemanticElements: virtualized headers cannot use native table layout.
                <div
                  key={`row-header-${rowIndex}`}
                  role="rowheader"
                  tabIndex={-1}
                  aria-rowindex={rowIndex + 1}
                  aria-colindex={1}
                  style={{
                    position: 'sticky',
                    left: 0,
                    top: `${virtualRow.start}px`,
                    width: `${virtualCol.size}px`,
                    height: `${virtualRow.size}px`,
                    display: 'flex',
                    alignItems: 'center',
                    padding: '8px',
                    fontWeight: 'bold',
                    background: '#f9fafb',
                    borderRight: '2px solid #d1d5db',
                    borderBottom: '1px solid #e5e7eb',
                    fontSize: '12px',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    color: '#374151',
                    zIndex: 2,
                  }}
                  title={`${rowIndex}. ${variables[rowIndex - 1].label}`}
                >
                  {rowIndex}. {variables[rowIndex - 1].label}
                </div>
              )
            }

            // Standard correlation cell
            const valRow = rowIndex - 1
            const valCol = colIndex - 1
            const val = coefficients[valRow]?.[valCol]
            const pVal = pValues[valRow]?.[valCol]
            const count = counts[valRow]?.[valCol]
            const lower = ciLower[valRow]?.[valCol]
            const upper = ciUpper[valRow]?.[valCol]
            const isDiagonalOrLower = valCol <= valRow
            const cellText = isDiagonalOrLower
              ? `${metric(val)}${valRow === valCol ? '' : significance(pVal)}`
              : ''

            return (
              // biome-ignore lint/a11y/useSemanticElements: virtualized cells cannot use native table layout.
              <div
                key={`cell-${rowIndex}-${colIndex}`}
                role="cell"
                aria-rowindex={rowIndex + 1}
                aria-colindex={colIndex + 1}
                style={{
                  position: 'absolute',
                  top: `${virtualRow.start}px`,
                  left: `${virtualCol.start}px`,
                  width: `${virtualCol.size}px`,
                  height: `${virtualRow.size}px`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '8px',
                  borderBottom: '1px solid #e5e7eb',
                  borderRight: colIndex === variables.length ? 'none' : '1px solid #e5e7eb',
                  fontSize: '12px',
                  background: valRow === valCol ? '#f9fafb' : '#fff',
                  color: '#4b5563',
                }}
                title={isDiagonalOrLower
                  ? lower == null || upper == null
                    ? `N=${count}`
                    : `N=${count}；${Math.round(confidenceLevel * 100)}% CI [${metric(lower)}, ${metric(upper)}]`
                  : undefined}
              >
                {cellText}
              </div>
            )
          })
        })}
      </div>
    </div>
  )
}
