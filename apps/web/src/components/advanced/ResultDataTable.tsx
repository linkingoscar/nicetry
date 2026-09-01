interface ResultDataTableProps {
  caption: string
  rows: Array<Record<string, unknown>>
}

function formatCell(value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(6)
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function ResultDataTable({ caption, rows }: ResultDataTableProps) {
  if (rows.length === 0) return null
  const columns = Array.from(new Set(rows.flatMap((row) => Object.keys(row))))

  return (
    <div className="adv-family-table-block">
      <h4>{caption}</h4>
      <div className="adv-table-wrap">
        <table className="adv-result-table" aria-label={caption}>
          <thead>
            <tr>
              {columns.map((column) => <th key={column}>{column}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const stableKey = columns.map((column) => formatCell(row[column])).join('|')
              return (
                <tr key={stableKey}>
                  {columns.map((column) => (
                    <td key={column} className="adv-est-num">{formatCell(row[column])}</td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
