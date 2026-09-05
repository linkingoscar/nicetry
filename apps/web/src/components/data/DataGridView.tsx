import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import type { DatasetVariable, DatasetVersion } from '../../types'
import { getDatasetRows } from '../../api/datasets'
import { ScrollableResultTable } from '../shared/ScrollableResultTable'
import styles from '../DataWorkspace.module.css'

const typeLabels: Record<DatasetVariable['inferredType'], string> = {
  continuous: '连续',
  binary: '二分类',
  nominal: '名义',
  ordinal: '有序',
  likert: 'Likert',
  id: 'ID',
  text: '文本',
}

function cellValue(
  row: Record<string, string | number | boolean | null>,
  variable: DatasetVariable,
) {
  const value = row[variable.originalName] ?? row[variable.id]
  if (value === null || value === undefined || value === '') return '—'
  return String(value)
}

interface DataGridViewProps {
  dataset: DatasetVersion
}

export function DataGridView({ dataset }: DataGridViewProps) {
  const [offset, setOffset] = useState(0)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<{ column?: string; direction: 'asc' | 'desc' }>({ direction: 'asc' })
  const pageSize = 100
  const rowsQuery = useQuery({
    queryKey: ['dataset-rows', dataset.id, offset, search, sort.column, sort.direction],
    queryFn: () => getDatasetRows(dataset.id, {
      offset,
      limit: pageSize,
      search: search.trim() || undefined,
      sortColumn: sort.column,
      sortDirection: sort.direction,
    }),
    placeholderData: (previous) => previous,
  })
  useEffect(() => {
    const timeout = window.setTimeout(() => setSearch(searchInput), 300)
    return () => window.clearTimeout(timeout)
  }, [searchInput])
  const rows = rowsQuery.data?.rows ?? dataset.preview
  const total = rowsQuery.data?.total ?? dataset.rowCount
  const previewCount = rows.length
  const duplicateCounts = new Map<string, number>()
  const previewRows = rows.map((row) => {
    const signature = JSON.stringify(dataset.variables.map((variable) => cellValue(row, variable)))
    const occurrence = duplicateCounts.get(signature) ?? 0
    duplicateCounts.set(signature, occurrence + 1)
    return { row, key: `${signature}:${occurrence}` }
  })

  return (
    <section className={styles.dataGridSection} aria-labelledby="data-grid-heading">
      <div className={styles.dataGridHeading}>
        <div>
          <p className="eyebrow">数据视图</p>
          <h2 id="data-grid-heading">当前数据</h2>
        </div>
        <p className={styles.previewSummary}>
          显示 {total ? offset + 1 : 0}–{Math.min(offset + previewCount, total)} / {total} 个案例 · {dataset.columnCount} 个变量
        </p>
      </div>

      <div className={styles.dataGridControls}>
        <label>
          查找案例
          <input
            type="search"
            value={searchInput}
            placeholder="搜索所有变量"
            onChange={(event) => {
              setSearchInput(event.target.value)
              setOffset(0)
            }}
          />
        </label>
        <button type="button" className="secondary-button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - pageSize))}>上一页</button>
        <button type="button" className="secondary-button" disabled={offset + pageSize >= total} onClick={() => setOffset(offset + pageSize)}>下一页</button>
        {rowsQuery.isFetching ? <span role="status">正在读取…</span> : null}
      </div>

      {previewCount > 0 ? (
        <ScrollableResultTable className={styles.dataGridWrap} label="当前数据预览，可横向滚动">
          <table className={styles.dataGridTable}>
            <thead>
              <tr>
                <th scope="col" className={styles.stickyColumn}>#</th>
                {dataset.variables.map((variable) => {
                  const effectiveType = variable.confirmedType ?? variable.inferredType
                  return (
                    <th scope="col" key={variable.id}>
                      <button
                        type="button"
                        className={styles.columnSortButton}
                        aria-label={`按${variable.label}排序`}
                        onClick={() => {
                          setSort((current) => ({
                            column: variable.id,
                            direction: current.column === variable.id && current.direction === 'asc' ? 'desc' : 'asc',
                          }))
                          setOffset(0)
                        }}
                      >
                        <strong>{variable.label}</strong>
                        {sort.column === variable.id ? <span>{sort.direction === 'asc' ? ' ↑' : ' ↓'}</span> : null}
                      </button>
                      <small>{variable.originalName}</small>
                      <span>{typeLabels[effectiveType]}</span>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {previewRows.map(({ row, key }, rowIndex) => (
                <tr key={key}>
                  <th scope="row" className={styles.stickyColumn}>{offset + rowIndex + 1}</th>
                  {dataset.variables.map((variable) => (
                    <td key={variable.id}>{cellValue(row, variable)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      ) : (
        <p className="empty-state">{rowsQuery.isError ? `数据读取失败：${rowsQuery.error.message}` : '没有匹配的案例。'}</p>
      )}
    </section>
  )
}
