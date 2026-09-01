import {
  formatAPAStat,
  formatAPASigStars,
} from '../../utils/apaFormatter'
import styles from './CorrelationHeatmap.module.css'

interface CorrelationHeatmapAccessibleTableProps {
  variables: Array<{ id: string; label: string }>
  coefficients: Array<Array<number | null>>
  pValues: Array<Array<number | null>>
}

export function CorrelationHeatmapAccessibleTable({
  variables,
  coefficients,
  pValues,
}: CorrelationHeatmapAccessibleTableProps) {
  return (
    <details className={styles.details}>
      <summary className={styles.detailsSummary}>
        查看相关矩阵全量可读文本与表格数据
      </summary>
      <div className={styles.tableWrap}>
        <table className={`sr-only-table ${styles.table}`}>
          <caption className="sr-only">相关系数矩阵数值明细表</caption>
          <thead>
            <tr>
              <th scope="col">变量名称</th>
              {variables.map((v, i) => (
                <th key={v.id} scope="col">{i + 1}. {v.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {variables.map((rowVar, rIdx) => (
              <tr key={rowVar.id}>
                <th scope="row">{rIdx + 1}. {rowVar.label}</th>
                {variables.map((colVar, cIdx) => {
                  if (cIdx > rIdx) return <td key={`cell-${rowVar.id}-${colVar.id}`}>—</td>
                  const val = coefficients[rIdx]?.[cIdx]
                  const pVal = pValues?.[rIdx]?.[cIdx]
                  return (
                    <td key={`cell-${rowVar.id}-${colVar.id}`}>
                      {formatAPAStat(val)}
                      {rIdx === cIdx ? '' : formatAPASigStars(pVal)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
