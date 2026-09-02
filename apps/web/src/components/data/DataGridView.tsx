import type { DatasetVariable, DatasetVersion } from '../../types'
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
  const previewCount = dataset.preview.length

  return (
    <section className={styles.dataGridSection} aria-labelledby="data-grid-heading">
      <div className={styles.dataGridHeading}>
        <div>
          <p className="eyebrow">数据视图</p>
          <h2 id="data-grid-heading">当前数据</h2>
        </div>
        <p className={styles.previewSummary}>
          预览 {previewCount} / {dataset.rowCount} 个案例 · {dataset.columnCount} 个变量
        </p>
      </div>

      {previewCount > 0 ? (
        <ScrollableResultTable className={styles.dataGridWrap} label="当前数据预览，可横向滚动">
          <table className={styles.dataGridTable}>
            <thead>
              <tr>
                <th scope="col">#</th>
                {dataset.variables.map((variable) => {
                  const effectiveType = variable.confirmedType ?? variable.inferredType
                  return (
                    <th scope="col" key={variable.id}>
                      <strong>{variable.label}</strong>
                      <small>{variable.originalName}</small>
                      <span>{typeLabels[effectiveType]}</span>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {dataset.preview.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  <th scope="row">{rowIndex + 1}</th>
                  {dataset.variables.map((variable) => (
                    <td key={variable.id}>{cellValue(row, variable)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </ScrollableResultTable>
      ) : (
        <p className="empty-state">当前数据版本没有可显示的预览行。</p>
      )}
    </section>
  )
}
