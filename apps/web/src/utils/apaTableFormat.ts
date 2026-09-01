/**
 * Utility functions for exporting tabular data into APA 7th Edition compliant formats:
 * - Word Native 3-line table HTML (with inline styles for direct pasting)
 * - LaTeX table with booktabs package (\toprule, \midrule, \bottomrule)
 * - Standard Markdown table
 * - TSV / Excel tab-separated values
 */

export interface APATableData {
  title?: string
  headers: string[]
  rows: string[][]
}

/**
 * Parses a markdown formatted table string into structured headers and rows.
 */
export function parseMarkdownTable(markdown: string): APATableData | null {
  if (!markdown || typeof markdown !== 'string') return null

  const lines = markdown
    .trim()
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.startsWith('|'))

  if (lines.length < 2) return null

  const parseRow = (line: string): string[] =>
    line
      .split('|')
      .slice(1, -1)
      .map((cell) => cell.trim())

  const headers = parseRow(lines[0])

  // Skip delimiter line (e.g., |---|---|)
  const contentLines = lines.slice(1).filter((line) => !/^[|\s-:]+$/.test(line))

  const rows = contentLines.map(parseRow)

  if (headers.length === 0 || rows.length === 0) return null

  return { headers, rows }
}

/**
 * Converts structured table data into APA 7th Edition Word-compatible HTML string.
 */
export function convertTableDataToWordHtml(data: APATableData): string {
  const { title, headers, rows } = data

  const titleHtml = title
    ? `<caption style="caption-side: top; text-align: left; font-weight: bold; font-family: 'Times New Roman', SimSun, serif; font-size: 11pt; margin-bottom: 8px;">${escapeHtml(title)}</caption>`
    : ''

  const ths = headers
    .map(
      (h, idx) =>
        `<th style="padding: 6px 12px; text-align: ${idx === 0 ? 'left' : 'right'}; font-weight: bold; border-top: 2.0pt solid #000000; border-bottom: 1.0pt solid #000000; background-color: transparent;">${escapeHtml(h)}</th>`,
    )
    .join('')

  const trs = rows
    .map((row, rowIdx) => {
      const isLastRow = rowIdx === rows.length - 1
      const borderBottomStyle = isLastRow ? 'border-bottom: 2.0pt solid #000000;' : 'border-bottom: none;'
      const tds = row
        .map((cell, colIdx) => {
          const align = colIdx === 0 ? 'left' : 'right'
          return `<td style="padding: 5px 12px; text-align: ${align}; ${borderBottomStyle}">${escapeHtml(cell)}</td>`
        })
        .join('')
      return `<tr>${tds}</tr>`
    })
    .join('\n      ')

  return `<table style="border-collapse: collapse; width: 100%; font-family: 'Times New Roman', SimSun, serif; font-size: 10.5pt; color: #000000; background-color: #ffffff; margin: 12px 0;">
  ${titleHtml}
  <thead>
    <tr>${ths}</tr>
  </thead>
  <tbody>
    ${trs}
  </tbody>
</table>`
}

/**
 * Converts structured table data into LaTeX booktabs format.
 */
export function convertTableDataToLaTeX(data: APATableData): string {
  const { title, headers, rows } = data
  const colAlignments = headers.map((_, idx) => (idx === 0 ? 'l' : 'r')).join('')

  const latexTitle = title ? `  \\caption{${escapeLaTeX(title)}}\n  \\label{tab:${slugify(title)}}\n` : ''
  const headerRow = `    ${headers.map(escapeLaTeX).join(' & ')} \\\\`
  const bodyRows = rows.map((row) => `    ${row.map(escapeLaTeX).join(' & ')} \\\\`).join('\n')

  return `\\begin{table}[htbp]
  \\centering
${latexTitle}  \\begin{tabular}{${colAlignments}}
    \\toprule
${headerRow}
    \\midrule
${bodyRows}
    \\bottomrule
  \\end{tabular}
\\end{table}`
}

/**
 * 与后端 tabular_security.escape_spreadsheet_formula 完全同策略：
 * 去除前导空格后首字符为 = + - @ \t \r \n 的单元格加前缀 '，
 * 防止粘贴进 Excel/Sheets 时被解释为公式（含空白/换行绕过形式）。
 */
export function escapeSpreadsheetFormula(value: string | number): string | number {
  if (typeof value !== 'string' || value === '') return value
  const candidate = value.replace(/^ +/, '')
  if (candidate.startsWith('=') || candidate.startsWith('+')
    || candidate.startsWith('-') || candidate.startsWith('@')
    || candidate.startsWith('\t') || candidate.startsWith('\r')
    || candidate.startsWith('\n')) {
    return `'${value}`
  }
  return value
}

/**
 * Converts structured table data to TSV (Excel paste compatible).
 */
export function convertTableDataToTSV(data: APATableData): string {
  const headerLine = data.headers.map(escapeSpreadsheetFormula).join('\t')
  const rowLines = data.rows
    .map((r) => r.map(escapeSpreadsheetFormula).join('\t'))
    .join('\n')
  return `${headerLine}\n${rowLines}`
}

/**
 * Converts structured table data to Markdown table.
 */
export function convertTableDataToMarkdown(data: APATableData): string {
  const { headers, rows } = data
  const headerLine = `| ${headers.join(' | ')} |`
  const delimiterLine = `| ${headers.map((_, i) => (i === 0 ? ':---' : '---:')).join(' | ')} |`
  const rowLines = rows.map((r) => `| ${r.join(' | ')} |`).join('\n')
  return `${headerLine}\n${delimiterLine}\n${rowLines}`
}

/**
 * Extract table data from a rendered DOM HTMLTableElement.
 */
export function extractTableDataFromDOM(tableEl: HTMLTableElement, title?: string): APATableData {
  const headerEls = Array.from(tableEl.querySelectorAll('thead th, thead td'))
  const headers = headerEls.map((th) => th.textContent?.trim() ?? '')

  const rowEls = Array.from(tableEl.querySelectorAll('tbody tr'))
  const rows = rowEls.map((tr) => {
    const cellEls = Array.from(tr.querySelectorAll('th, td'))
    return cellEls.map((cell) => cell.textContent?.trim() ?? '')
  })

  return { title, headers, rows }
}

/**
 * Copies table data to clipboard in the specified format.
 */
export async function copyAPATableToClipboard(
  data: APATableData,
  format: 'word' | 'latex' | 'markdown' | 'tsv',
): Promise<{ success: boolean; message: string }> {
  try {
    if (format === 'word') {
      const htmlString = convertTableDataToWordHtml(data)
      const plainText = convertTableDataToMarkdown(data)

      if (typeof ClipboardItem !== 'undefined' && navigator.clipboard && navigator.clipboard.write) {
        const htmlBlob = new Blob([htmlString], { type: 'text/html' })
        const textBlob = new Blob([plainText], { type: 'text/plain' })
        await navigator.clipboard.write([
          new ClipboardItem({
            'text/html': htmlBlob,
            'text/plain': textBlob,
          }),
        ])
        return { success: true, message: '🎉 已复制 Word 原生 APA 三线表！可直接 Ctrl+V 粘贴到 Word' }
      } else {
        await navigator.clipboard.writeText(htmlString)
        return { success: true, message: '已复制 HTML 格式三线表代码' }
      }
    } else if (format === 'latex') {
      const latex = convertTableDataToLaTeX(data)
      await navigator.clipboard.writeText(latex)
      return { success: true, message: '🎉 已复制 LaTeX (booktabs) 表格源码！' }
    } else if (format === 'markdown') {
      const md = convertTableDataToMarkdown(data)
      await navigator.clipboard.writeText(md)
      return { success: true, message: '🎉 已复制 Markdown 表格！' }
    } else if (format === 'tsv') {
      const tsv = convertTableDataToTSV(data)
      await navigator.clipboard.writeText(tsv)
      return { success: true, message: '🎉 已复制 Excel / TSV 数据！' }
    }
    return { success: false, message: '未知的导出格式' }
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : String(err)
    return { success: false, message: `复制失败: ${errorMsg}` }
  }
}

export function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

function escapeLaTeX(text: string): string {
  return text
    .replace(/\\/g, '\\textbackslash{}')
    .replace(/%/g, '\\%')
    .replace(/\$/g, '\\$')
    .replace(/&/g, '\\&')
    .replace(/#/g, '\\#')
    .replace(/_/g, '\\_')
    .replace(/\{/g, '\\{')
    .replace(/\}/g, '\\}')
    .replace(/~/g, '\\textasciitilde{}')
    .replace(/\^/g, '\\textasciicircum{}')
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '_')
    .replace(/^-+|-+$/g, '')
}
