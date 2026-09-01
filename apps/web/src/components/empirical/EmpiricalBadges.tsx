import { metric } from './resultFormatters'

export function renderSigBadge(value: number | null | undefined) {
  if (value === null || value === undefined) return null
  if (value < 0.001) return <span className="sig-badge sig-p001" title="p < 0.001">***</span>
  if (value < 0.01) return <span className="sig-badge sig-p01" title="p < 0.01">**</span>
  if (value < 0.05) return <span className="sig-badge sig-p05" title="p < 0.05">*</span>
  return null
}

function confidencePercent(confidenceLevel: number | null | undefined) {
  const level = confidenceLevel ?? 0.95
  return Math.round(level * 100)
}

export function VisualCIBar({
  lower,
  upper,
  confidenceLevel,
}: {
  lower: number | null | undefined
  upper: number | null | undefined
  confidenceLevel?: number | null
}) {
  if (lower === null || lower === undefined || upper === null || upper === undefined) return null
  const crossesZero = lower <= 0 && upper >= 0
  const levelLabel = `${confidencePercent(confidenceLevel)}%`
  return (
    <span
      className={`visual-ci-bar ${crossesZero ? 'crosses-zero' : 'significant'}`}
      title={`${levelLabel} 置信区间: [${lower.toFixed(3)}, ${upper.toFixed(3)}] ${crossesZero ? '(区间跨 0，未达到统计显著性)' : '(区间未跨 0，达到统计显著性)'}`}
    >
      <span className="visual-ci-tag">{crossesZero ? '⚪ CI跨0' : '🟢 CI未跨0'}</span>
      {levelLabel} [{metric(lower)}, {metric(upper)}]
    </span>
  )
}

export function SegmentLoader() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '200px', width: '100%' }}>
      <div style={{ textAlign: 'center' }}>
        <div className="spinner" style={{ border: '3px solid rgba(31, 45, 90,0.1)', borderTop: '3px solid #1f2d5a', borderRadius: '50%', width: '32px', height: '32px', animation: 'spin 1s linear infinite', margin: '0 auto 12px' }} />
        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
        <span style={{ color: '#6b7280', fontSize: '14px' }}>正在载入本节证据包...</span>
      </div>
    </div>
  )
}
