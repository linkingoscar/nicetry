import type { StudyIntent } from '../../types/study-context'

interface ResearchStartProps {
  onSelect: (intent: StudyIntent) => void
}

export function ResearchStart({ onSelect }: ResearchStartProps) {
  return (
    <main className="research-start" aria-labelledby="research-start-heading">
      <header>
        <p className="eyebrow">研径 ResearchPath</p>
        <h1 id="research-start-heading">本地点按式实证分析工作台</h1>
        <p>导入数据后直接进入数据工作区，再从统一“分析”入口选择方法。研究规划和功效工具不再作为开始分析前的必经步骤。</p>
      </header>
      <div className="research-start-grid">
        <button type="button" onClick={() => onSelect('analyze')}>
          <span className="eyebrow">主要入口</span>
          <strong>导入数据并开始分析</strong>
          <small>支持当前已实现的数据格式；导入后先查看数据，再按需选择描述、信度、相关、回归、PROCESS、SEM 或高级方法。</small>
          <em>数据 → 分析 → 输出</em>
          <span className="research-start-action">进入工作台 →</span>
        </button>
        <button type="button" onClick={() => onSelect('plan')}>
          <span className="eyebrow">无数据工具</span>
          <strong>功效与研究规划</strong>
          <small>在没有活动数据时使用样本量、功效、精度和研究规划能力；不会创建空数据集。</small>
          <em>工具入口 · 不阻塞已有数据分析</em>
          <span className="research-start-action">打开工具 →</span>
        </button>
      </div>
    </main>
  )
}
