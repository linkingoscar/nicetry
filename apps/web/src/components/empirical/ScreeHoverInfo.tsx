import { formatAPAStat } from '../../utils/apaFormatter'

export interface ScreeHoverState {
  factor: number
  value: number
  simulatedValue?: number
  varianceExplainedPct?: number
  cx: number
  cy: number
}

export function ScreeHoverInfo({ hoverState }: { hoverState: ScreeHoverState }) {
  return (
    <div
      className="glass-panel"
      style={{
        position: 'absolute',
        top: '40px',
        right: '24px',
        background: 'var(--text-main)',
        color: '#ffffff',
        padding: '8px 12px',
        borderRadius: '8px',
        fontSize: '11px',
        boxShadow: 'var(--shadow-hover)',
        zIndex: 10,
        display: 'grid',
        gap: '2px',
        pointerEvents: 'none',
      }}
    >
      <div style={{ color: '#38bdf8', fontWeight: 700 }}>
        成分 / 因子 #{hoverState.factor}
      </div>
      <div>特征值 (Eigenvalue): <strong style={{ color: '#4a6dde' }}>{formatAPAStat(hoverState.value)}</strong></div>
      {typeof hoverState.simulatedValue === 'number' ? (
        <div style={{ color: '#fcd34d' }}>平行分析阈值: {formatAPAStat(hoverState.simulatedValue)}</div>
      ) : null}
      {typeof hoverState.varianceExplainedPct === 'number' ? (
        <div style={{ color: '#cbd5e1' }}>方差贡献率: {hoverState.varianceExplainedPct.toFixed(2)}%</div>
      ) : null}
    </div>
  )
}
