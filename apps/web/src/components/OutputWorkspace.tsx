import { useMemo } from 'react'

import type { DatasetVersion, MeasurementVersion } from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { empiricalProcedures } from './empirical/empiricalProcedures'
import { readEmpiricalHistory } from './empirical/empiricalRunHistory'

interface OutputWorkspaceProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  onOpenProcedure: (procedure: EmpiricalProcedure) => void
}

export function OutputWorkspace({ dataset, measurement, onOpenProcedure }: OutputWorkspaceProps) {
  const historyKey = `researchpath.empirical.runs.v1:${dataset.id}:${measurement?.version ?? null}`
  const history = useMemo(() => readEmpiricalHistory(historyKey), [historyKey])
  const procedureById = useMemo(() => new Map(empiricalProcedures.map((item) => [item.id, item])), [])

  return (
    <main className="analysis-shell" aria-labelledby="output-workspace-heading">
      <header className="analysis-shell-header">
        <div>
          <p className="eyebrow">统一结果入口</p>
          <h1 id="output-workspace-heading">输出</h1>
          <p>集中回看已经提交的分析运行。第一阶段先接入现有实证运行索引，旧结果保持不可变；模型与高级任务会继续沿用现有结果组件并逐步汇入这里。</p>
        </div>
      </header>

      {history.length ? (
        <section className="context-catalog" aria-label="最近实证运行">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">最近运行</p>
              <h2>当前数据的实证结果</h2>
            </div>
            <span className="status-badge">{history.length} 次</span>
          </div>
          <div className="method-grid">
            {history.map((entry, index) => {
              const definition = procedureById.get(entry.procedure)
              return (
                <article className="method-card" key={entry.id}>
                  <div>
                    <p className="eyebrow">运行 {history.length - index}</p>
                    <h3>{definition?.label ?? entry.procedure}</h3>
                    <p>{new Date(entry.createdAt).toLocaleString()}</p>
                  </div>
                  <div className="method-card-actions">
                    <button type="button" className="secondary-button" onClick={() => onOpenProcedure(entry.procedure)}>
                      打开分析与结果
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        </section>
      ) : (
        <section className="centered-state">
          <h2>还没有运行任何分析</h2>
          <p>从“分析”选择一个方法并显式运行后，运行记录会出现在这里。</p>
        </section>
      )}
    </main>
  )
}
