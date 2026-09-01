interface InvalidationNoticeProps {
  validity: 'ready' | 'incomplete' | 'stale'
  missingRequirements: string[]
  warnings: Array<{ code: string; message: string }>
  invalidation?: {
    upstreamChanges: string[]
    affectedObjects: string[]
    historyStatus: 'available' | 'not_available'
    requiredAction: 'confirm' | 'migrate' | 'rerun'
  } | null
  invalidationReasons?: string[]
}

export function InvalidationNotice({
  validity,
  missingRequirements,
  warnings,
  invalidation,
  invalidationReasons = [],
}: InvalidationNoticeProps) {
  if (validity === 'ready' && missingRequirements.length === 0 && warnings.length === 0) return null
  const stale = validity === 'stale'
  const details = invalidation ?? (stale ? {
    upstreamChanges: ['上游数据、结构或对象版本发生变化'],
    affectedObjects: ['当前分析草稿及其派生运行结果'],
    historyStatus: 'available' as const,
    requiredAction: 'rerun' as const,
  } : null)
  return (
    <aside className={`context-invalidation context-invalidation-${stale ? 'stale' : 'attention'}`} role={stale ? 'alert' : 'status'}>
      <strong>{stale ? '当前配置已过期' : '分析尚未完全就绪'}</strong>
      {details ? (
        <dl>
          <div><dt>变更来源</dt><dd>{details.upstreamChanges.join('、')}</dd></div>
          <div><dt>受影响对象</dt><dd>{details.affectedObjects.join('、')}</dd></div>
          <div><dt>历史结果</dt><dd>{details.historyStatus === 'available' ? '仍可查看，但不会被新上下文冒充为当前结果。' : '当前不可用。'}</dd></div>
          <div><dt>下一步</dt><dd>{details.requiredAction === 'confirm' ? '确认上游对象后再进入方法。' : details.requiredAction === 'migrate' ? '迁移到新版本并重新确认。' : '创建新草稿并重新运行。'}</dd></div>
        </dl>
      ) : null}
      {missingRequirements.length > 0 ? <p>待处理：{missingRequirements.join('、')}</p> : null}
      {warnings.length > 0 ? <p>警告：{warnings.map(warning => warning.message).join('；')}</p> : null}
      {invalidationReasons.length > 0 ? <p>系统记录：{invalidationReasons.join('、')}</p> : null}
    </aside>
  )
}
