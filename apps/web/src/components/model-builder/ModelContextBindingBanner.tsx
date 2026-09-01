import type { ResolvedAnalysisContext } from '../../types/analysis-context'

interface ModelContextBindingBannerProps {
  analysisContext: ResolvedAnalysisContext
  blocked: boolean
  stale: boolean
}

export function ModelContextBindingBanner({ analysisContext, blocked, stale }: ModelContextBindingBannerProps) {
  const contextValue = analysisContext.studyContext?.value

  return (
    <section className="model-context-binding" aria-label="PROCESS 与 SEM 上下文绑定">
      <details>
        <summary>模型数据绑定详情</summary>
        <p className="eyebrow">当前分析上下文</p>
        <strong>{contextValue ? `${contextValue.timeStructure} · ${contextValue.dependenceStructure} · ${contextValue.design}` : '上下文尚未完整解析'}</strong>
        <small>
          结构角色：subject={analysisContext.structure?.roles.subjectId ?? '未绑定'} · cluster={analysisContext.structure?.roles.clusterId ?? '未绑定'} · time={analysisContext.structure?.roles.timeId ?? '未绑定'}
        </small>
      </details>
      {analysisContext.validity !== 'ready' ? (
        <p className="method-warning" role="alert">
          当前上下文尚未就绪{analysisContext.missingRequirements?.length ? `：还缺少 ${analysisContext.missingRequirements.join('、')}。` : '。'}请回到数据页完成结构角色、测量或样本版本确认后再运行。
        </p>
      ) : blocked ? (
        <p className="method-warning" role="alert">当前上下文包含纵向或聚类结构，PROCESS/SEM 执行入口已锁定；请从服务端方法目录选择与面板/嵌套结构匹配的模型。</p>
      ) : stale ? (
        <p className="method-warning" role="alert">当前模型草稿绑定的 contextHash 已过期；请重新创建草稿，历史模型不会被原地改写。</p>
      ) : null}
    </section>
  )
}
