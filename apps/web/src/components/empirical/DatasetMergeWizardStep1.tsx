import type { FormEvent } from 'react'
import type { DatasetVersion } from '../../types'
import styles from './DatasetMergeWizard.module.css'

interface DatasetMergeStep1Props {
  primaryDataset: DatasetVersion
  targetFile: File | null
  importPending: boolean
  importError: string | null
  onTargetFileChange: (file: File | null) => void
  onCancel: () => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void
}

export function DatasetMergeStep1({
  primaryDataset,
  targetFile,
  importPending,
  importError,
  onTargetFileChange,
  onCancel,
  onSubmit,
}: DatasetMergeStep1Props) {
  return (
    <div>
      <p className={styles.stepDescription}>
        请上传您需要与当前数据集 <strong>{primaryDataset.originalFile.name}</strong>（共 {primaryDataset.rowCount} 行）合并的第二个数据文件。支持 CSV、XLSX、SAV、DTA 和 POR。
      </p>
      <form onSubmit={onSubmit} className={styles.uploadForm}>
        <div className={styles.dropzone}>
          <input
            id="merge-target-file"
            type="file"
            accept=".csv,.xlsx,.sav,.dta,.por"
            onChange={(e) => onTargetFileChange(e.target.files?.[0] || null)}
            className={styles.fileInput}
          />
          <label htmlFor="merge-target-file" className={styles.dropzoneLabel}>
            <div className={styles.fileIcon}>📂</div>
            <strong className={styles.fileName}>
              {targetFile ? targetFile.name : '点击选择或拖拽文件到此处'}
            </strong>
            <span className={styles.fileMeta}>
              {targetFile ? `${(targetFile.size / 1024).toFixed(1)} KB` : '支持 CSV, Excel, SPSS, Stata 格式'}
            </span>
          </label>
        </div>

        {importError !== null && (
          <div className={styles.errorBox}>
            导入失败: {importError}
          </div>
        )}

        <div className={styles.actionRow}>
          <button
            type="button"
            onClick={onCancel}
            className={styles.secondaryButton}
          >
            取消
          </button>
          <button
            type="submit"
            disabled={!targetFile || importPending}
            className={[
              styles.primaryButton,
              importPending ? styles.primaryButtonPending : '',
              targetFile ? '' : styles.primaryButtonCursorNotAllowed,
            ].join(' ')}
          >
            {importPending ? '分析中...' : '下一步'}
          </button>
        </div>
      </form>
    </div>
  )
}
