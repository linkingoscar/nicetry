import styles from './DataWorkspace.module.css'

interface DataWorkspaceEmptyStateProps {
  demoLabel: string
  demoDescription: string
  loadingDemo: boolean
  onLoadDemo?: () => void
}

export function DataWorkspaceEmptyState({
  demoLabel,
  demoDescription,
  loadingDemo,
  onLoadDemo,
}: DataWorkspaceEmptyStateProps) {
  return (
    <div className="empty-data-state">
      <strong>尚未创建数据版本</strong>
      <p>导入后会在这里显示变量类型建议、缺失率、唯一值和人工确认入口。</p>
      {onLoadDemo ? (
        <>
          <p className={styles.demoDescription}>{demoDescription}</p>
          <button
            type="button"
            className={`run-button ${styles.demoButton}`}
            disabled={loadingDemo}
            onClick={onLoadDemo}
          >
            {loadingDemo ? '正在导入时间结构示例项目…' : demoLabel}
          </button>
        </>
      ) : null}
    </div>
  )
}
