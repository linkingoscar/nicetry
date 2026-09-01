import type { DatasetMergeReport } from '../../types'
import styles from './DatasetMergeWizard.module.css'

interface DatasetMergeStep3Props {
  mergeReport: DatasetMergeReport
  onCancel: () => void
  onApply: () => void
}

export function DatasetMergeStep3({
  mergeReport,
  onCancel,
  onApply,
}: DatasetMergeStep3Props) {
  const total = mergeReport.matchedCount + mergeReport.primaryOnlyCount + mergeReport.targetOnlyCount
  return (
    <div>
      <div className={styles.successPanel}>
        <span className={styles.successIcon}>✓</span>
        <div>
          <strong className={styles.successTitle}>数据集对齐合并已成功完成！</strong>
          <span className={styles.successSub}>合并后的临时版本已就绪，以下为数据交叉诊断摘要。</span>
        </div>
      </div>

      <div className={styles.diagnosticsGrid}>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>匹配成功的样本数</span>
          <strong className={`${styles.metricValue} ${styles.metricValueGreen}`}>{mergeReport.matchedCount}</strong>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>仅主文件包含的样本数</span>
          <strong className={`${styles.metricValue} ${styles.metricValueYellow}`}>{mergeReport.primaryOnlyCount}</strong>
        </div>
        <div className={styles.metricCard}>
          <span className={styles.metricLabel}>仅目标文件包含的样本数</span>
          <strong className={`${styles.metricValue} ${styles.metricValueBlue}`}>{mergeReport.targetOnlyCount}</strong>
        </div>
      </div>

      <div className={styles.overlapPanel}>
        <span className={styles.overlapHeader}>关联重叠比例可视化</span>
        <div className={styles.overlapBar}>
          {mergeReport.primaryOnlyCount > 0 && (
            <div
              title={`仅主文件: ${mergeReport.primaryOnlyCount}`}
              className={styles.overlapSegmentPrimary}
              style={{ width: `${(mergeReport.primaryOnlyCount / total) * 100}%` }}
            />
          )}
          {mergeReport.matchedCount > 0 && (
            <div
              title={`匹配成功: ${mergeReport.matchedCount}`}
              className={styles.overlapSegmentMatched}
              style={{ width: `${(mergeReport.matchedCount / total) * 100}%` }}
            />
          )}
          {mergeReport.targetOnlyCount > 0 && (
            <div
              title={`仅目标文件: ${mergeReport.targetOnlyCount}`}
              className={styles.overlapSegmentTarget}
              style={{ width: `${(mergeReport.targetOnlyCount / total) * 100}%` }}
            />
          )}
        </div>
        <div className={styles.overlapLegend}>
          <span>🟡 仅主文件 ({mergeReport.primaryOnlyCount})</span>
          <span>🟢 完美重叠匹配 ({mergeReport.matchedCount})</span>
          <span>🔵 仅目标文件 ({mergeReport.targetOnlyCount})</span>
        </div>
      </div>

      {mergeReport.warnings.length > 0 && (
        <div className={styles.warningPanel}>
          <span className={styles.warningTitle}>
            ⚠️ 合并对齐冲突警告：
          </span>
          <ul className={styles.warningList}>
            {mergeReport.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className={styles.actionRow}>
        <button
          type="button"
          onClick={onCancel}
          className={styles.secondaryButton}
        >
          放弃合并
        </button>
        <button
          type="button"
          onClick={onApply}
          className={styles.primaryButton}
        >
          应用并确认新版本
        </button>
      </div>
    </div>
  )
}
