import type { DatasetVersion } from '../../types'
import styles from './DatasetMergeWizard.module.css'

interface DatasetMergeStep2Props {
  targetDataset: DatasetVersion
  primaryCols: string[]
  commonCols: string[]
  subjectKey: string
  waveKey: string
  mergePending: boolean
  mergeError: string | null
  onSubjectKeyChange: (value: string) => void
  onWaveKeyChange: (value: string) => void
  onBack: () => void
  onMerge: () => void
}

export function DatasetMergeStep2({
  targetDataset,
  primaryCols,
  commonCols,
  subjectKey,
  waveKey,
  mergePending,
  mergeError,
  onSubjectKeyChange,
  onWaveKeyChange,
  onBack,
  onMerge,
}: DatasetMergeStep2Props) {
  return (
    <div>
      <p className={styles.stepDescriptionMuted}>
        已载入目标文件 <strong>{targetDataset.originalFile.name}</strong>（共 {targetDataset.rowCount} 行）。
        请指定用于关联这两个数据源的变量键（如用户 ID、样本 ID ）。
      </p>

      <div className={styles.keyPanel}>
        <div className={styles.fieldGroup}>
          <label htmlFor="subject-key-select" className={styles.fieldLabel}>
            被试主键 (Subject Key) <span className={styles.required}>*</span>
          </label>
          <select
            id="subject-key-select"
            value={subjectKey}
            onChange={(e) => onSubjectKeyChange(e.target.value)}
            className={styles.select}
          >
            <option value="">-- 请选择重叠的变量 --</option>
            {commonCols.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
            {commonCols.length === 0 && primaryCols.map(col => (
              <option key={col} value={col}>{col} (仅存在于主文件)</option>
            ))}
          </select>
          <span className={styles.hint}>
            必须同时存在于两个数据集中，用于唯一标识同一位被试（如 <code>userId</code>）。
          </span>
        </div>

        <div className={styles.fieldGroup}>
          <label htmlFor="wave-key-select" className={styles.fieldLabel}>
            波次变量 (Wave Key) <span className={styles.optional}>(可选)</span>
          </label>
          <select
            id="wave-key-select"
            value={waveKey}
            onChange={(e) => onWaveKeyChange(e.target.value)}
            className={styles.select}
          >
            <option value="">-- 不使用波次（单波合并） --</option>
            {commonCols.map(col => (
              <option key={col} value={col}>{col}</option>
            ))}
          </select>
          <span className={styles.hint}>
            若为多波次追踪研究，请指定时间或波次变量（如 <code>wave</code>），以便将同一被试不同时间的行正确对齐。
          </span>
        </div>
      </div>

      {mergeError !== null && (
        <div className={`${styles.errorBox} ${styles.errorBoxSpaced}`}>
          合并失败: {mergeError}
        </div>
      )}

      <div className={styles.actionRowBetween}>
        <button
          type="button"
          onClick={onBack}
          className={styles.secondaryButton}
        >
          上一步
        </button>
        <button
          type="button"
          onClick={onMerge}
          disabled={!subjectKey || mergePending}
          className={[
            styles.primaryButton,
            mergePending ? styles.primaryButtonPending : '',
            subjectKey ? '' : styles.primaryButtonCursorNotAllowed,
          ].join(' ')}
        >
          {mergePending ? '正在对齐和计算...' : '开始执行合并'}
        </button>
      </div>
    </div>
  )
}
