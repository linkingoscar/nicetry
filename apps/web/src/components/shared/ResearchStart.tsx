import type { StudyIntent } from '../../types/study-context'

interface ResearchStartProps {
  onSelect: (intent: StudyIntent) => void
}

const START_OPTIONS: Array<{
  intent: StudyIntent
  eyebrow: string
  title: string
  description: string
  route: string
}> = [
  {
    intent: 'plan',
    eyebrow: '尚未收集数据',
    title: '规划新研究',
    description: '从研究问题、设计与测量方案出发，计算样本量、功效和精度。',
    route: '研究问题 → 数据结构 → 测量设计 → 功效与分析计划',
  },
  {
    intent: 'analyze',
    eyebrow: '已经拥有数据',
    title: '分析已有数据',
    description: '先确认时间与依赖结构，再完成匹配的数据、测量和模型准备。',
    route: '数据结构 → 导入与质检 → 测量准备 → 分析与报告',
  },
]

export function ResearchStart({ onSelect }: ResearchStartProps) {
  return (
    <main className="research-start" aria-labelledby="research-start-heading">
      <header>
        <p className="eyebrow">开始一项研究</p>
        <h1 id="research-start-heading">你现在处于哪个阶段？</h1>
        <p>两条流程使用不同的前置条件。规划不要求数据；已有数据分析会根据数据结构限制可用方法。</p>
      </header>
      <div className="research-start-grid">
        {START_OPTIONS.map((option) => (
          <button type="button" key={option.intent} onClick={() => onSelect(option.intent)}>
            <span className="eyebrow">{option.eyebrow}</span>
            <strong>{option.title}</strong>
            <small>{option.description}</small>
            <em>{option.route}</em>
            <span className="research-start-action">进入工作流 →</span>
          </button>
        ))}
      </div>
    </main>
  )
}
