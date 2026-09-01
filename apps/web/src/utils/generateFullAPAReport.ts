import { escapeHtml } from './apaTableExport'
import { APA_MANUSCRIPT_STYLES } from './apaManuscriptStyles'

export interface APAManuscriptData {
  title?: string
  reportId: string
  datasetName?: string
  sampleCount?: number
  kmo?: number | null
  harmanFirstFactor?: number | null
  descriptives?: Array<{
    label: string
    n: number
    missing: number
    mean: number | null
    sd: number | null
    minimum: number | null
    maximum: number | null
    skewness: number | null
    kurtosis: number | null
  }>
  correlationTable?: {
    variables: Array<{ id: string; label: string }>
    coefficients: Array<Array<number | null>>
    pValues?: Array<Array<number | null>>
  }
  academicInterpretation?: string
}

function metric(v: number | null | undefined, digits = 2): string {
  if (typeof v !== 'number' || Number.isNaN(v)) return '—'
  return v.toFixed(digits)
}

function sigStars(p: number | null | undefined): string {
  if (typeof p !== 'number') return ''
  if (p < 0.001) return '***'
  if (p < 0.01) return '**'
  if (p < 0.05) return '*'
  return ''
}

export function openAPAManuscriptReport(data: APAManuscriptData) {
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>APA 7th 实证研究报告 - ${escapeHtml(data.title ?? '学术盲审手稿')}</title>
  <style>${APA_MANUSCRIPT_STYLES}</style>
</head>
<body>
  <div class="action-bar">
    <button onclick="window.print()">🖨️ 打印 / 另存为 PDF 手稿</button>
  </div>

  <div class="running-head">
    <span>RUNNING HEAD: EMPIRICAL MANUSCRIPT REPORT</span>
    <span>APA 7TH EDITION</span>
  </div>

  <h1 class="title">实证研究统计分析报告 (APA 7th Standard Manuscript)</h1>
  <div class="author-note">
    <p>数据集: ${escapeHtml(data.datasetName ?? '问卷数据集')} | 报告存根 ID: ${escapeHtml(data.reportId)}</p>
    <p>匿名评审版 (Double-Blind Review Ready Manuscript)</p>
  </div>

  <h2>1. 描述统计与样本正态性检验 (Descriptives & Distribution)</h2>
  <table class="apa-table">
    <caption>Table 1. 变量描述统计、偏度与峰度诊断 (N = ${data.sampleCount ?? '—'})</caption>
    <thead>
      <tr>
        <th>变量名称</th>
        <th>N</th>
        <th>M</th>
        <th>SD</th>
        <th>Skewness (偏度)</th>
        <th>Kurtosis (峰度)</th>
      </tr>
    </thead>
    <tbody>
      ${
        data.descriptives
          ? data.descriptives
              .map(
                (d) => `
        <tr>
          <td>${escapeHtml(d.label)}</td>
          <td>${d.n}</td>
          <td>${metric(d.mean)}</td>
          <td>${metric(d.sd)}</td>
          <td>${metric(d.skewness)}</td>
          <td>${metric(d.kurtosis)}</td>
        </tr>`,
              )
              .join('')
          : '<tr><td colspan="6">暂无描述统计数据</td></tr>'
      }
    </tbody>
  </table>

  <div class="page-break"></div>

  <h2>2. 变量相关系数矩阵 (Correlation Matrix)</h2>
  ${
    data.correlationTable
      ? `<table class="apa-table">
    <caption>Table 2. 构念间相关系数矩阵与显著性检验</caption>
    <thead>
      <tr>
        <th>变量</th>
        ${data.correlationTable.variables.map((_v, i) => `<th>${i + 1}</th>`).join('')}
      </tr>
    </thead>
    <tbody>
      ${data.correlationTable.variables
        .map(
          (vRow, r) => `
        <tr>
          <td>${r + 1}. ${escapeHtml(vRow.label)}</td>
          ${data.correlationTable?.variables
            .map((_, c) => {
              if (c > r) return '<td>—</td>'
              if (c === r) return '<td>1.00</td>'
              const rVal = data.correlationTable?.coefficients[r]?.[c]
              const pVal = data.correlationTable?.pValues?.[r]?.[c]
              return `<td>${typeof rVal === 'number' ? rVal.toFixed(2) + sigStars(pVal) : '—'}</td>`
            })
            .join('')}
        </tr>`,
        )
        .join('')}
    </tbody>
  </table>
  <p class="table-note">* p &lt; .05, ** p &lt; .01, *** p &lt; .001。</p>`
      : '<p>暂无相关矩阵数据</p>'
  }

  <h2>3. 测量效度与共同方法偏差检验 (Reliability & Common Method Bias)</h2>
  <p>样本 Kaiser-Meyer-Olkin (KMO) 抽样适当性度量值为 <strong>${metric(data.kmo)}</strong>。采用 Harman 单因子检验（Harman's Single-Factor Test）对共同方法偏差进行评估，未旋转的首个主因子解释累积方差为 <strong>${metric(data.harmanFirstFactor, 1)}%</strong>（学术常规标准临界值为 &lt; 40%）。</p>

  <h2>4. 学术论文结果讨论与标准表述 (Academic Findings Interpretation)</h2>
  <div style="background: #fcfcfc; border-left: 3px solid #000000; padding: 12px 18px; margin-top: 12pt;">
    ${data.academicInterpretation ? escapeHtml(data.academicInterpretation).replace(/\n/g, '<br/>') : '当前结果缺少经后端授权生成的学术解读，此节需人工撰写解释，不得由系统生成肯定性结论。'}
  </div>
</body>
</html>`

  const reportWindow = window.open('', '_blank')
  if (reportWindow) {
    reportWindow.document.write(html)
    reportWindow.document.close()
  }
}
