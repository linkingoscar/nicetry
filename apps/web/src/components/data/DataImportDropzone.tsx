import { useState, type FormEvent } from 'react'

interface DataImportDropzoneProps {
  selectedFile: File | null
  onFileSelect: (file: File | null) => void
  onImport: (event: FormEvent<HTMLFormElement>) => void
  isPending: boolean
  dataStructureLabel: string
  dependenceStructure?: string
}

export function DataImportDropzone({
  selectedFile,
  onFileSelect,
  onImport,
  isPending,
  dataStructureLabel,
  dependenceStructure,
}: DataImportDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isDragging) setIsDragging(true)
  }

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) {
      onFileSelect(file)
    }
  }

  return (
    <div className="upload-panel">
      <div>
        <p className="eyebrow">数据版本</p>
        <h1 id="data-heading">导入{dataStructureLabel}</h1>
        <p className="muted">支持 CSV、XLSX、SAV、DTA 和 POR。原文件将计算 SHA-256 并以只读方式保存在本机。</p>
        {dependenceStructure === 'nested' ? (
          <p className="method-warning">当前研究存在聚类 / 嵌套。导入后请将团队、班级或机构标识确认为 ID；正式分析前还需指定 cluster 角色并检查组规模与 ICC。</p>
        ) : null}
      </div>
      <form className="upload-form" onSubmit={onImport}>
        <section
          aria-label="数据文件拖放区域"
          className={`dropzone-container ${isDragging ? 'is-dragging' : ''} ${selectedFile ? 'has-file' : ''}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <div className="dropzone-icon">
            <svg viewBox="0 0 32 32" aria-hidden="true">
              {selectedFile
                ? <path d="M8 3h10l6 6v20H8zM18 3v7h6M12 16h8M12 21h8" />
                : <path d="M3 9h10l3 3h13v16H3zM3 9V6h10l3 3" />}
            </svg>
          </div>
          <div className="dropzone-text">
            <strong>{selectedFile ? selectedFile.name : '点击或拖放数据文件至此处'}</strong>
            <p>{selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB` : '点击选择或将文件拖入此框内'}</p>
          </div>
          <div className="format-badges">
            <span className="format-badge">SAV</span>
            <span className="format-badge">XLSX</span>
            <span className="format-badge">CSV</span>
            <span className="format-badge">DTA</span>
            <span className="format-badge">POR</span>
          </div>
          <label htmlFor="dataset-file" className="sr-only">选择数据文件</label>
          <input
            id="dataset-file"
            type="file"
            accept=".csv,.xlsx,.sav,.dta,.por"
            style={{ position: 'absolute', inset: 0, opacity: 0, cursor: 'pointer', width: '100%', height: '100%' }}
            onChange={(event) => {
              onFileSelect(event.target.files?.[0] ?? null)
            }}
          />
        </section>
        <button className="run-button" type="submit" disabled={!selectedFile || isPending}>
          {isPending ? '正在读取和画像…' : '导入并创建数据版本'}
        </button>
        <div role="status" aria-live="polite" className="sr-only">
          {isPending ? '正在读取文件并进行结构诊断与变量画像，请稍候…' : ''}
        </div>
      </form>
    </div>
  )
}
