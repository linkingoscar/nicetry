import { useState } from 'react'
import {
  copyAPATableToClipboard,
  extractTableDataFromDOM,
  parseMarkdownTable,
  type APATableData,
} from '../../utils/apaTableExport'
import { CopyIcon, CheckIcon } from './Icons'
import { showToast } from './Toast'

interface APATableExporterProps {
  data?: APATableData
  markdownTable?: string
  getTableElement?: () => HTMLTableElement | null
  title?: string
  size?: 'sm' | 'md'
  className?: string
}

export function APATableExporter({
  data,
  markdownTable,
  getTableElement,
  title,
  size = 'sm',
  className = '',
}: APATableExporterProps) {
  const [copiedFormat, setCopiedFormat] = useState<string | null>(null)

  const resolveTableData = (): APATableData | null => {
    if (data) {
      return { ...data, title: data.title ?? title }
    }
    if (markdownTable) {
      const parsed = parseMarkdownTable(markdownTable)
      if (parsed) return { ...parsed, title: parsed.title ?? title }
    }
    if (getTableElement) {
      const el = getTableElement()
      if (el) return extractTableDataFromDOM(el, title)
    }
    return null
  }

  const handleCopy = async (format: 'word' | 'latex' | 'markdown' | 'tsv') => {
    const tableData = resolveTableData()
    if (!tableData) {
      showToast('未找到表格数据，无法导出', 'error')
      return
    }

    const res = await copyAPATableToClipboard(tableData, format)
    if (res.success) {
      setCopiedFormat(format)
      showToast(res.message, 'success')
      setTimeout(() => {
        setCopiedFormat(null)
      }, 2500)
    } else {
      showToast(res.message, 'error')
    }
  }

  return (
    <div className={`apa-table-exporter is-${size} ${className}`}>
      <span className="apa-table-exporter-label">APA 7th 表格导出：</span>

      <button
        type="button"
        title="复制为 Word 原生三线表 (直接 Ctrl+V 粘贴到 Word/WPS)"
        className={`apa-export-button is-word${copiedFormat === 'word' ? ' is-copied' : ''}`}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          handleCopy('word')
        }}
      >
        {copiedFormat === 'word' ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckIcon size={13} /> 已复制 Word</span> : 'Word 三线表'}
      </button>

      <button
        type="button"
        title="复制为 LaTeX (booktabs) 宏包表格源码"
        className={`apa-export-button${copiedFormat === 'latex' ? ' is-copied' : ''}`}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          handleCopy('latex')
        }}
      >
        {copiedFormat === 'latex' ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckIcon size={13} /> 已复制 LaTeX</span> : 'LaTeX (booktabs)'}
      </button>

      <button
        type="button"
        title="复制为 Markdown 表格"
        className={`apa-export-button${copiedFormat === 'markdown' ? ' is-copied' : ''}`}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          handleCopy('markdown')
        }}
      >
        {copiedFormat === 'markdown' ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckIcon size={13} /> 已复制 MD</span> : <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CopyIcon size={13} /> Markdown</span>}
      </button>

      <button
        type="button"
        title="复制为 Excel / TSV 制表符分割数据"
        className={`apa-export-button${copiedFormat === 'tsv' ? ' is-copied' : ''}`}
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          handleCopy('tsv')
        }}
      >
        {copiedFormat === 'tsv' ? <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}><CheckIcon size={13} /> 已复制 TSV</span> : 'Excel'}
      </button>
    </div>
  )
}
