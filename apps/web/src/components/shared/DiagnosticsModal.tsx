import type React from 'react'
import type { ResultBundle } from '../../types'
import { StethoscopeIcon } from './Icons'
import { analyzeDiagnostics } from './diagnosticsAnalyzer'

interface DiagnosticsModalProps {
  isOpen: boolean
  onClose: () => void
  result?: ResultBundle
  error?: Error | null
}

export const DiagnosticsModal: React.FC<DiagnosticsModalProps> = ({
  isOpen,
  onClose,
  result,
  error,
}) => {
  if (!isOpen) return null
  const diagnostics = analyzeDiagnostics(result, error)

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="diagnostics-modal-title"
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
      }}
    >
      <button
        type="button"
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(15, 23, 42, 0.65)',
          backdropFilter: 'blur(4px)',
          border: 0,
          padding: 0,
          cursor: 'pointer',
        }}
        aria-label="关闭弹窗"
        onClick={onClose}
      />
      <div
        role="document"
        style={{
          position: 'relative',
          zIndex: 1,
          width: '100%',
          maxWidth: '720px',
          maxHeight: '85vh',
          background: 'var(--bg-surface, #ffffff)',
          border: '1px solid var(--border-card, #d5d7de)',
          borderRadius: '16px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '18px 24px',
            borderBottom: '1px solid var(--border-subtle, #e2e8f0)',
            background: 'var(--bg-subtle, #f8f8fa)',
          }}
        >
          <div>
            <span className="eyebrow" style={{ margin: 0 }}>Model Health & Diagnostics</span>
            <h2 id="diagnostics-modal-title" style={{ margin: '4px 0 0', fontSize: '18px', color: 'var(--text-main, #0f172a)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <StethoscopeIcon size={20} /> 统计模型诊断报告与修复指引
            </h2>
          </div>
          <button
            type="button"
            className="secondary-button"
            style={{ padding: '4px 10px', fontSize: '12px' }}
            onClick={onClose}
          >
            ✕ 关闭
          </button>
        </header>

        <main style={{ padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {diagnostics.map((item) => (
            <div
              key={item.id}
              style={{
                padding: '16px',
                borderRadius: '12px',
                border: '1px solid',
                borderColor: item.severity === 'error' ? '#fca5a5' : item.severity === 'warning' ? '#fde68a' : '#bbc9f7',
                background: item.severity === 'error' ? '#fef2f2' : item.severity === 'warning' ? '#fffbeb' : '#f0f3fd',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                <strong style={{ fontSize: '14px', color: item.severity === 'error' ? '#991b1b' : item.severity === 'warning' ? '#92400e' : '#162865' }}>
                  {item.title}
                </strong>
                <span
                  style={{
                    padding: '2px 8px',
                    borderRadius: '999px',
                    fontSize: '10px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: item.severity === 'error' ? '#991b1b' : item.severity === 'warning' ? '#92400e' : '#162865',
                    background: item.severity === 'error' ? '#fee2e2' : item.severity === 'warning' ? '#fef3c7' : '#dce3fc',
                  }}
                >
                  {item.severity}
                </span>
              </div>

              <p style={{ margin: 0, fontSize: '13px', color: 'var(--text-body, #334155)', lineHeight: 1.5 }}>
                {item.description}
              </p>

              <div
                style={{
                  marginTop: '4px',
                  padding: '10px 12px',
                  background: 'rgba(255, 255, 255, 0.75)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: 'var(--brand-primary, #0d1f5c)',
                  fontWeight: 600,
                  border: '1px dashed rgba(13, 31, 92, 0.3)',
                }}
              >
                💡 <strong>修正指引：</strong> {item.remediation}
              </div>
            </div>
          ))}
        </main>

        <footer
          style={{
            padding: '14px 24px',
            borderTop: '1px solid var(--border-subtle, #e2e8f0)',
            background: 'var(--bg-subtle, #f8f8fa)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span style={{ fontSize: '12px', color: 'var(--text-muted, #64748b)' }}>
            诊断结果依据 R 估算包 warnings 及样本分布自动生成
          </span>
          <button
            type="button"
            className="run-button"
            style={{ width: 'auto', padding: '8px 16px', fontSize: '12px' }}
            onClick={onClose}
          >
            知道了
          </button>
        </footer>
      </div>
    </div>
  )
}
