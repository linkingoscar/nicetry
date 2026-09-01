import { useState } from 'react'
import type { ResultBundle } from '../types'
import { ResultProcessSection } from './results/ResultProcessSection'
import { ResultSemSection } from './results/ResultSemSection'
import { AcademicInterpretation } from './shared/AcademicInterpretation'
import { APATableExporter } from './shared/APATableExporter'
import { DiagnosticsModal } from './shared/DiagnosticsModal'
import { CopyIcon, StethoscopeIcon } from './shared/Icons'
import { showToast } from './shared/Toast'

interface ResultPanelProps {
  result?: ResultBundle
  isRunning: boolean
  error?: Error | null
  onRun?: () => void
  title?: string
  runLabel?: string
}

export function ResultPanel({
  result,
  isRunning,
  error,
  onRun,
  title = '模型分析结果',
  runLabel = '重新运行当前冻结版本',
}: ResultPanelProps) {
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false)

  return (
    <aside className="result-panel" aria-labelledby="analysis-heading">
      <div>
        <p className="eyebrow">统计执行</p>
        <h2 id="analysis-heading">{title}</h2>
        <p className="muted">
          {result?.semResult
            ? '结构方程估计；估计器、缺失处理、标准误与拟合诊断以本次运行记录为准。'
            : 'PROCESS 路径估计；系数尺度、标准误与间接效应区间以本次运行记录为准。'}
        </p>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        {onRun ? <button className="run-button" type="button" onClick={onRun} disabled={isRunning} style={{ flex: 1 }}>
          {isRunning ? 'R 引擎正在计算…' : runLabel}
        </button> : null}
        <button
          className="secondary-button"
          type="button"
          style={{ whiteSpace: 'nowrap', padding: '12px 14px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}
          onClick={() => setIsDiagnosticsOpen(true)}
          title="查看模型健康状态与详细诊断"
        >
          <StethoscopeIcon size={16} /> 统计诊断报告
        </button>
      </div>

      {error ? <p className="error-message" role="alert">{error.message}</p> : null}

      {result?.academicInterpretation ? (
        <section className="equation-result interpretation-section">
          <details open>
            <summary className="academic-interpretation-summary">
              <span>中文自动解读与 APA 报告规范</span>
            </summary>
            <div className="academic-interpretation-actions">
              <button
                type="button"
                className="academic-interpretation-copy-btn"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                onClick={() => {
                  navigator.clipboard.writeText(result.academicInterpretation || '')
                  showToast('已复制学术文本到剪贴板，可直接粘贴到 Word！', 'success')
                }}
              >
                <CopyIcon size={14} /> 复制解读文本
              </button>
              {result.apaTables ? (
                <APATableExporter markdownTable={result.apaTables} title={`${title} - APA 三线表`} />
              ) : null}
            </div>
            <AcademicInterpretation text={result.academicInterpretation} />
          </details>
        </section>
      ) : null}

      {result?.semResult ? (
        <ResultSemSection result={result} />
      ) : result ? (
        <ResultProcessSection result={result} title={title} />
      ) : null}

      {result?.warnings.map((warning) => (
        <p className="method-warning" key={warning.code}>{warning.message}</p>
      ))}

      <DiagnosticsModal
        isOpen={isDiagnosticsOpen}
        onClose={() => setIsDiagnosticsOpen(false)}
        result={result}
        error={error}
      />
    </aside>
  )
}
