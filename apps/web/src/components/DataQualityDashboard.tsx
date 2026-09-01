import type { DataQualityRun } from '../types'

interface DataQualityDashboardProps {
  qualityRun: DataQualityRun | null
  missingRate: number | null
  straightlineRatio: number | null
  duplicateCount: number | null
}

export function DataQualityDashboard({
  qualityRun,
  missingRate,
  straightlineRatio,
  duplicateCount,
}: DataQualityDashboardProps) {
  return (
    <div
      className="data-health-dashboard"
      style={{
        margin: '16px 0',
        padding: '16px 20px',
        background: 'var(--bg-surface)',
        border: '1px solid #d5d7de',
        borderRadius: '14px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '16px',
        alignItems: 'center',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* Circular SVG Gauge Dial */}
        <div style={{ position: 'relative', width: '80px', height: '80px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <svg width="80" height="80" viewBox="0 0 36 36">
            <title>数据健康度仪表盘</title>
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="var(--border-subtle)"
              strokeWidth="3.5"
            />
            <path
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              fill="none"
              stroke="var(--brand-accent)"
              strokeWidth="3.5"
              strokeDasharray="0, 100"
              strokeLinecap="round"
            />
          </svg>
          <div style={{ position: 'absolute', textAlign: 'center' }}>
            <span style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-main)' }}>
              {qualityRun ? '✓' : '—'}
            </span>
            <span style={{ fontSize: '9px', display: 'block', color: 'var(--text-muted)' }}>{qualityRun ? '指标已生成' : '尚未运行'}</span>
          </div>
        </div>

        <div style={{ display: 'grid', gap: '2px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>数据健康度评估</span>
          <strong style={{ fontSize: '15px', color: 'var(--brand-primary)' }}>
            {qualityRun ? '质量已审计' : '尚未运行质量检查'}
          </strong>
          <span style={{ fontSize: '11px', color: qualityRun ? 'var(--brand-accent)' : 'var(--text-muted)', fontWeight: 600 }}>
            {qualityRun ? '指标来自当前质量运行' : '运行后才会显示案例级指标'}
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', padding: '8px 12px', borderRadius: '10px', fontSize: '11px', minWidth: '120px' }}>
          <span style={{ color: 'var(--text-muted)', display: 'block' }}>缺失受损率</span>
          <strong style={{ fontSize: '13px', color: 'var(--text-main)' }}>
            {missingRate === null ? '—' : `${(missingRate * 100).toFixed(1)}%`}
          </strong>
        </div>
        <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', padding: '8px 12px', borderRadius: '10px', fontSize: '11px', minWidth: '120px' }}>
          <span style={{ color: 'var(--text-muted)', display: 'block' }}>直穿作答率</span>
          <strong style={{ fontSize: '13px', color: 'var(--text-main)' }}>
            {straightlineRatio === null ? '—' : `${(straightlineRatio * 100).toFixed(1)}%`}
          </strong>
        </div>
        <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', padding: '8px 12px', borderRadius: '10px', fontSize: '11px', minWidth: '120px' }}>
          <span style={{ color: 'var(--text-muted)', display: 'block' }}>重复/离群案例</span>
          <strong style={{ fontSize: '13px', color: 'var(--text-main)' }}>
            {duplicateCount === null ? '—' : `${duplicateCount} 个`}
          </strong>
        </div>
      </div>
    </div>
  )
}
