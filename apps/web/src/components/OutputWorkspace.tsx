import { useMemo } from 'react'

import type { DatasetVersion, MeasurementVersion } from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { empiricalDraftStatusForOutput } from './analyses/analysisDraftStatus'
import {
  analysisDocumentsForDataset,
  analysisRunsForDocument,
  loadEmpiricalAnalysisIndex,
} from './analyses/analysisDocuments'

interface OutputWorkspaceProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  onOpenProcedure: (procedure: EmpiricalProcedure) => void
}

export function OutputWorkspace({ dataset, measurement, onOpenProcedure }: OutputWorkspaceProps) {
  const index = useMemo(
    () => loadEmpiricalAnalysisIndex(dataset, measurement),
    [dataset, measurement],
  )
  const documents = useMemo(
    () => analysisDocumentsForDataset(index, dataset, measurement),
    [dataset, index, measurement],
  )
  const runCount = documents.reduce(
    (count, document) => count + analysisRunsForDocument(index, document.id).length,
    0,
  )

  return (
    <main className="analysis-shell" aria-labelledby="output-workspace-heading">
      <header className="analysis-shell-header">
        <div>
          <p className="eyebrow">分析对象与运行</p>
          <h1 id="output-workspace-heading">输出</h1>
          <p>一项分析可以保留多次不可变运行。修改当前草稿不会覆盖旧运行；旧浏览器运行索引会先作为兼容引用归入对应分析对象。</p>
        </div>
      </header>

      {documents.length ? (
        <section className="context-catalog" aria-label="当前数据的分析对象">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">当前数据</p>
              <h2>分析与运行</h2>
            </div>
            <span className="status-badge">{documents.length} 项分析 · {runCount} 次运行</span>
          </div>
          <div className="method-grid">
            {documents.map((document) => {
              const runs = analysisRunsForDocument(index, document.id)
              const latestRun = runs[0]
              const draft = empiricalDraftStatusForOutput(
                dataset,
                measurement,
                document.procedure,
                latestRun?.id,
              )
              return (
                <article className="method-card" key={document.id}>
                  <div>
                    <p className="eyebrow">{document.categoryId.replaceAll('-', ' ')}</p>
                    <h3>{document.title}</h3>
                    <p>{runs.length} 次运行{latestRun ? ` · 最近 ${new Date(latestRun.createdAt).toLocaleString()}` : ''}</p>
                    <div className="method-card-status-row">
                      {draft.dirtySinceLastRun ? <span className="context-method-status method-status-needs-setup">有未运行更改</span> : null}
                      {draft.hasSavedDraft ? <span className="context-method-status">草稿已保存</span> : null}
                    </div>
                    {latestRun ? (
                      <p className="muted">最新运行 {latestRun.id.slice(0, 12)} · 历史索引引用</p>
                    ) : null}
                  </div>

                  {runs.length ? (
                    <details>
                      <summary>查看运行历史</summary>
                      <ol>
                        {runs.map((run) => (
                          <li key={run.id}>
                            <code>{run.id.slice(0, 12)}</code>
                            {' · '}{new Date(run.createdAt).toLocaleString()}
                            {' · '}历史状态待服务端结果索引确认
                          </li>
                        ))}
                      </ol>
                    </details>
                  ) : null}

                  <div className="method-card-actions">
                    <button type="button" className="secondary-button" onClick={() => onOpenProcedure(document.procedure)}>
                      编辑设置 / 打开当前结果
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
          <p>从“分析”选择一个方法并显式运行后，这里会先创建分析对象，再把每次运行归到它的历史中。</p>
        </section>
      )}
    </main>
  )
}
