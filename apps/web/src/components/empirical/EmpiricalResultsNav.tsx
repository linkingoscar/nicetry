export type EmpiricalResultTab =
  | 'overview'
  | 'correlation'
  | 'measurement'
  | 'groups'
  | 'regression'
  | 'advanced'
  | 'longitudinal'
  | 'diary'

export type TabStatus = 'available' | 'warning' | 'not_requested'

const resultTabs: Array<{ id: EmpiricalResultTab; step: string; label: string; shortLabel: string }> = [
  { id: 'overview', step: '1', label: '描述与正态性', shortLabel: '正态性' },
  { id: 'correlation', step: '2', label: '相关与矩阵', shortLabel: '相关' },
  { id: 'measurement', step: '3', label: '信效度 (EFA/CFA)', shortLabel: '信效度' },
  { id: 'groups', step: '4', label: '组间与聚合', shortLabel: '组间' },
  { id: 'regression', step: '5', label: '分层回归', shortLabel: '回归' },
  { id: 'advanced', step: '6', label: '高级与稳健性', shortLabel: '高级' },
  { id: 'longitudinal', step: '7', label: '纵向面板', shortLabel: '纵向' },
  { id: 'diary', step: '8', label: '日记 / ESM', shortLabel: '日记' },
]

export function EmpiricalResultsNav({
  activeTab,
  pending,
  statusMap = {},
  onChange,
}: {
  activeTab: EmpiricalResultTab
  pending: boolean
  statusMap?: Partial<Record<EmpiricalResultTab, TabStatus>>
  onChange: (tab: EmpiricalResultTab) => void
}) {
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const currentIndex = resultTabs.findIndex((t) => t.id === activeTab)
    if (currentIndex === -1) return

    let nextIndex = currentIndex
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault()
      nextIndex = (currentIndex + 1) % resultTabs.length
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault()
      nextIndex = (currentIndex - 1 + resultTabs.length) % resultTabs.length
    } else if (e.key === 'Home') {
      e.preventDefault()
      nextIndex = 0
    } else if (e.key === 'End') {
      e.preventDefault()
      nextIndex = resultTabs.length - 1
    }

    if (nextIndex !== currentIndex && resultTabs[nextIndex]) {
      onChange(resultTabs[nextIndex].id)
      const nextBtn = document.getElementById(`empirical-tab-${resultTabs[nextIndex].id}`)
      if (nextBtn) nextBtn.focus()
    }
  }

  return (
    <div
      className="empirical-result-tabs"
      role="tablist"
      aria-label="实证结果分区"
      onKeyDown={handleKeyDown}
    >
      {resultTabs.map((tab) => {
        const status = statusMap[tab.id] ?? 'available'
        const badgeText = status === 'available' ? '✓ 有结果' : status === 'warning' ? '⚠️ 需关注' : '• 未配置'
        const badgeColor = status === 'available' ? '#162865' : status === 'warning' ? '#92400e' : 'var(--text-caption, #475569)'
        const badgeBg = status === 'available' ? '#dce3fc' : status === 'warning' ? '#fef3c7' : '#f1f5f9'
        const isSelected = activeTab === tab.id

        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            id={`empirical-tab-${tab.id}`}
            aria-selected={isSelected}
            aria-controls={isSelected ? `empirical-panel-${tab.id}` : undefined}
            tabIndex={isSelected ? 0 : -1}
            disabled={pending}
            onClick={() => onChange(tab.id)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <span style={{ opacity: 0.75, fontSize: '10px', fontFamily: 'monospace' }}>{tab.step}.</span>
            <span className="result-tab-label">{tab.label}</span>
            <span className="result-tab-short">{tab.shortLabel}</span>

            <span
              style={{
                fontSize: '10px',
                fontWeight: 700,
                padding: '2px 7px',
                borderRadius: '999px',
                color: badgeColor,
                background: badgeBg,
                marginLeft: '2px',
              }}
            >
              {badgeText}
            </span>
          </button>
        )
      })}
    </div>
  )
}
