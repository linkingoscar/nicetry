import type { ReactNode } from 'react'

export type DiagnosticAlertType = 'warning' | 'important' | 'good' | 'note'

interface DiagnosticAlertCardProps {
  type?: DiagnosticAlertType
  title: string
  subtitle?: string
  children: ReactNode
  recommendation?: string
  className?: string
}

const typeStyles: Record<DiagnosticAlertType, { border: string; bg: string; text: string; icon: string }> = {
  warning: {
    border: '#d97706',
    bg: '#fffbeb',
    text: '#92400e',
    icon: '⚠️',
  },
  important: {
    border: '#2563eb',
    bg: '#eff6ff',
    text: '#1e40af',
    icon: '💡',
  },
  good: {
    border: '#052796',
    bg: '#ecf0fd',
    text: '#061b5f',
    icon: '✓',
  },
  note: {
    border: '#64748b',
    bg: '#f8fafc',
    text: '#334155',
    icon: 'ℹ️',
  },
}

export function DiagnosticAlertCard({
  type = 'note',
  title,
  subtitle,
  children,
  recommendation,
  className = '',
}: DiagnosticAlertCardProps) {
  const style = typeStyles[type]

  return (
    <div
      className={`diagnostic-alert-card diagnostic-alert-${type} ${className}`}
      style={{
        margin: '14px 0',
        padding: '14px 16px',
        background: style.bg,
        borderLeft: `4px solid ${style.border}`,
        borderRadius: '8px',
        color: style.text,
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.03)',
        display: 'grid',
        gap: '6px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ fontSize: '15px' }}>{style.icon}</span>
        <strong style={{ fontSize: '13px', fontWeight: 700 }}>{title}</strong>
        {subtitle ? (
          <span style={{ fontSize: '11px', opacity: 0.85, marginLeft: 'auto' }}>
            {subtitle}
          </span>
        ) : null}
      </div>

      <div style={{ fontSize: '12px', lineHeight: '1.6', opacity: 0.95 }}>
        {children}
      </div>

      {recommendation ? (
        <div
          style={{
            marginTop: '4px',
            paddingTop: '8px',
            borderTop: `1px dashed ${style.border}40`,
            fontSize: '11px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'baseline',
            gap: '6px',
          }}
        >
          <span>🎯 学术建议：</span>
          <span>{recommendation}</span>
        </div>
      ) : null}
    </div>
  )
}
