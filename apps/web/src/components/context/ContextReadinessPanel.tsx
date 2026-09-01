import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { InvalidationNotice } from './InvalidationNotice'
import { RoleBindingSummary } from './RoleBindingSummary'

interface ContextReadinessPanelProps {
  context: ResolvedAnalysisContext
  onPrepare?: () => void
}

export function ContextReadinessPanel({ context, onPrepare }: ContextReadinessPanelProps) {
  return (
    <section className="context-readiness-panel" aria-labelledby="context-readiness-heading">
      <div className="context-readiness-heading">
        <div>
          <h2 id="context-readiness-heading">{context.validity === 'ready' ? '数据可用于分析' : '数据设置需要确认'}</h2>
          <p className="muted">{context.measurement ? '已绑定测量' : '使用原始变量'} · {context.imputation ? '使用插补数据' : '未使用插补'}</p>
        </div>
        {onPrepare ? <button type="button" className="secondary-button" onClick={onPrepare}>{context.validity === 'ready' ? '查看数据准备' : '前往数据准备'}</button> : null}
      </div>
      <InvalidationNotice
        validity={context.validity}
        missingRequirements={context.missingRequirements}
        warnings={context.warnings}
        invalidation={context.invalidation}
      />
      <details className="context-diagnostics">
        <summary>版本与诊断详情</summary>
      <div className="context-readiness-grid">
        <div><span>数据版本</span><strong>{context.dataset.id}</strong></div>
        <div><span>结构版本</span><strong>{context.structure?.revision ?? '未确认'}</strong></div>
        <div><span>测量版本</span><strong>{context.measurement?.id ?? '未绑定'}</strong></div>
        <div><span>分析样本</span><strong>{context.sample.id}</strong></div>
        <div><span>插补状态</span><strong>{context.imputation ? '已绑定' : '未使用'}</strong></div>
      </div>
      <RoleBindingSummary roles={context.structure?.roles} />
      <p className="context-hash"><span>contextHash</span> <code>{context.contextHash}</code></p>
      </details>
    </section>
  )
}
