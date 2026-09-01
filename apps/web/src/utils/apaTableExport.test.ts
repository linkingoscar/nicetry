import { describe, expect, it } from 'vitest'
import {
  parseMarkdownTable,
  convertTableDataToWordHtml,
  convertTableDataToLaTeX,
  convertTableDataToTSV,
  convertTableDataToMarkdown,
  type APATableData,
} from './apaTableExport'

const mockData: APATableData = {
  title: '三线表中介检验结果',
  headers: ['路径', '估计值 (B)', '标准误 (SE)', '95% Boot CI'],
  rows: [
    ['路径 a (X -> M)', '0.610', '0.082', '[0.450, 0.770]'],
    ['路径 b (M -> Y)', '0.720', '0.075', '[0.570, 0.860]'],
    ['直接效应 c′', '0.210', '0.091', '[0.030, 0.390]'],
    ['间接效应 a×b', '0.439', '0.068', '[0.310, 0.580]'],
  ],
}

describe('apaTableExport', () => {
  describe('parseMarkdownTable', () => {
    it('parses valid markdown table', () => {
      const md = `
| 变量 | N | M | SD |
|---|---|---|---|
| X | 300 | 3.52 | 0.81 |
| Y | 300 | 4.10 | 0.65 |
`
      const parsed = parseMarkdownTable(md)
      expect(parsed).not.toBeNull()
      expect(parsed?.headers).toEqual(['变量', 'N', 'M', 'SD'])
      expect(parsed?.rows).toHaveLength(2)
      expect(parsed?.rows[0]).toEqual(['X', '300', '3.52', '0.81'])
    })

    it('returns null for invalid or empty input', () => {
      expect(parseMarkdownTable('')).toBeNull()
      expect(parseMarkdownTable('just text')).toBeNull()
    })
  })

  describe('convertTableDataToWordHtml', () => {
    it('generates HTML containing APA 3-line inline styles and title', () => {
      const html = convertTableDataToWordHtml(mockData)
      expect(html).toContain('border-collapse: collapse')
      expect(html).toContain('border-top: 2.0pt solid #000000')
      expect(html).toContain('border-bottom: 2.0pt solid #000000')
      expect(html).toContain('Times New Roman')
      expect(html).toContain('三线表中介检验结果')
      expect(html).toContain('间接效应 a×b')
    })
  })

  describe('convertTableDataToLaTeX', () => {
    it('generates booktabs LaTeX table code', () => {
      const latex = convertTableDataToLaTeX(mockData)
      expect(latex).toContain('\\begin{table}[htbp]')
      expect(latex).toContain('\\toprule')
      expect(latex).toContain('\\midrule')
      expect(latex).toContain('\\bottomrule')
      expect(latex).toContain('路径 a (X -> M) & 0.610 & 0.082 & [0.450, 0.770] \\\\')
    })
  })

  describe('convertTableDataToTSV', () => {
    it('generates tab-separated text', () => {
      const tsv = convertTableDataToTSV(mockData)
      expect(tsv).toContain('路径\t估计值 (B)\t标准误 (SE)\t95% Boot CI')
      expect(tsv).toContain('路径 a (X -> M)\t0.610\t0.082\t[0.450, 0.770]')
    })

    it('escapes formula-like cells before clipboard export', () => {
      const data: APATableData = {
        headers: ['=SUM(A1:A2)', 'ordinary', '\t=1+1', '  +2', '@cmd', '-3', 'normal'],
        rows: [['=1+1', '+SUM(B1)', 'plain', '=cmd', 'x', 'y', '\r=z']],
      }
      const tsv = convertTableDataToTSV(data)
      const lines = tsv.split('\n')
      expect(lines[0]).toBe(`'=SUM(A1:A2)\tordinary\t'\t=1+1\t'  +2\t'@cmd\t'-3\tnormal`)
      expect(lines[1]).toBe(`'=1+1\t'+SUM(B1)\tplain\t'=cmd\tx\ty\t'\r=z`)
    })
  })

  describe('convertTableDataToMarkdown', () => {
    it('generates markdown table text', () => {
      const md = convertTableDataToMarkdown(mockData)
      expect(md).toContain('| 路径 | 估计值 (B) | 标准误 (SE) | 95% Boot CI |')
      expect(md).toContain('| :--- | ---: | ---: | ---: |')
    })
  })
})
