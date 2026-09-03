import { useEffect, useMemo, useState } from 'react'

import type { DatasetVersion, MeasurementVersion } from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { empiricalDraftStatusForOutput } from './analyses/analysisDraftStatus'
import {
  analysisDocumentFreshness,
  analysisDocumentsForProject,
  analysisRunFreshness,
  analysisRunsForDocument,
  loadEmpiricalAnalysisIndex,
  setAnalysisPrimaryRun,
  updateAnalysisDocumentMetadata,
} from './analyses/analysisDocuments'
import { readAnalysisRunDetails } from './analyses/analysisRunDetails'
import { useOutputRunJobs } from './analyses/useOutputRunJobs'

interface OutputWorkspaceProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  onOpenProcedure: (procedure: EmpiricalProcedure, analysisId?: string) => void
}

function runStatusLabel(status?: string) {
  if (status === 'queued') return '排队中'
  if (status === 'running') return '运行中'
  if (status === 'cancelling') return '取消中'
  if (status === 'succeeded') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'cancelled') return '已取消'
  return '历史状态待服务端结果索引确认'
}

export function OutputWorkspace({ dataset, measurement, onOpenProcedure }: OutputWorkspaceProps) {
  const [index, setIndex] = useState(() => loadEmpiricalAnalysisIndex(dataset, measurement))
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setIndex(loadEmpiricalAnalysisIndex(dataset, measurement))
    setSelectedRunId(null)
  }, [dataset, measurement])

  const runDetails = useMemo(
    () => readAnalysisRunDetails(dataset.projectId),
    [dataset.projectId, index],
  )
  const detailsByRun = useMemo(
    () => new Map(runDetails.map((detail) => [detail.runId, detail])),
    [runDetails],
  )
  const documents = useMemo(
    () => analysisDocumentsForProject(index, dataset.projectId),
    [dataset.projectId, index],
  )
  const normalizedSearch = search.trim().toLocaleLowerCase()
  const filteredDocuments = useMemo(() => documents.filter((document) => {
    if (!normalizedSearch) return true
    const runText = analysisRunsForDocument(index, document.id).map((run) => run.id).join(' ')
    return `${document.title} ${document.methodId} ${document.procedure} ${runText}`
      .toLocaleLowerCase()
      .includes(normalizedSearch)
  }), [documents, index, normalizedSearch])

  const allRuns = documents.flatMap((document) => analysisRunsForDocument(index, document.id))
  const currentRunIds = allRuns
    .filter((run) => analysisRunFreshness(run, dataset, measurement) === 'current')
    .map((run) => run.id)
  const serverJobsByRun = useOutputRunJobs(currentRunIds, dataset.id, measurement?.version ?? null)
  const runCount = allRuns.length

  const selectedRun = selectedRunId ? index.runs.find((run) => run.id === selectedRunId) : undefined
  const selectedDocument = selectedRun ? documents.find((document) => document.id === selectedRun.analysisId) : undefined
  const selectedDetail = selectedRun ? detailsByRun.get(selectedRun.id) : undefined
  const selectedServerJob = selectedRun ? serverJobsByRun.get(selectedRun.id) : undefined
  const selectedFreshness = selectedRun ? analysisRunFreshness(selectedRun, dataset, measurement) : undefined

  const updateDocument = (analysisId: string, patch: { title?: string; pinned?: boolean }) => {
    setIndex(updateAnalysisDocumentMetadata(dataset.projectId, analysisId, patch))
  }
  const updatePrimaryRun = (analysisId: string, runId: string | null) => {
    setIndex(setAnalysisPrimaryRun(dataset.projectId, analysisId, runId))
  }

  return (
    <main className="analysis-shell" aria-labelledby="output-workspace-heading">
      <header className="analysis-shell-header">
        <div>
          <p className="eyebrow">分析对象与运行</p>
          <h1 id="output-workspace-heading">输出</h1>
          <p>一项分析可以保留多次不可变运行。旧数据或量表版本的结果继续可见，并明确标记为“基于旧设置”。</p>
        </div>
      </header>

      {selectedRun && selectedDocument ? (
        <section className="context-catalog" aria-label="选中的运行">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">当前运行</p>
              <h2>{selectedDocument.title}</h2>
              <p className="muted">{new Date(selectedRun.createdAt).toLocaleString()} · {runStatusLabel(selectedServerJob?.status ?? selectedDetail?.runStatus)}</p>
            </div>
            <button type="button" className="secondary-button" onClick={() => setSelectedRunId(null)}>关闭详情</button>
          </div>
          <div className="method-card-status-row">
            <span className="context-method-status">运行 {selectedRun.id.slice(0, 12)}</span>
            <span className={`context-method-status${selectedFreshness === 'stale' ? ' method-status-needs-setup' : ''}`}>
              {selectedFreshness === 'stale' ? '基于旧设置' : '当前数据/量表'}
            </span>
            {selectedDocument.primaryRunId === selectedRun.id ? <span className="context-method-status">主要结果</span> : null}
            {selectedDetail ? <span className="context-method-status">草稿修订 {selectedDetail.draftRevision}</span> : null}
            {selectedServerJob ? <span className="context-method-status">服务端已确认</span> : null}
            {selectedDetail?.qualityStatus === 'warning' ? <span className="context-method-status method-status-needs-setup">含警告</span> : null}
          </div>
          {selectedDetail ? (
            <div>
              <p>结果 ID：{selectedDetail.resultId ?? '当前运行尚未产生结果 ID'}</p>
              <p>警告：{selectedDetail.warningCodes.length ? selectedDetail.warningCodes.join('、') : '无已记录警告'}</p>
              <p className="muted">这份运行详情来自提交后的冻结规格与任务状态；只有当前数据上下文的运行会主动向服务端恢复状态。</p>
            </div>
          ) : (
            <p className="muted">该记录目前只有旧本地运行索引。服务端未能确认冻结规格或结果身份，因此这里不会补造运行详情。</p>
          )}
          <div className="method-card-actions">
            <button
              type="button"
              className="secondary-button"
              onClick={() => updatePrimaryRun(
                selectedDocument.id,
                selectedDocument.primaryRunId === selectedRun.id ? null : selectedRun.id,
              )}
            >
              {selectedDocument.primaryRunId === selectedRun.id ? '取消主要结果' : '设为主要结果'}
            </button>
            <button
              type="button"
              className="secondary-button"
              onClick={() => selectedFreshness === 'stale'
                ? onOpenProcedure(selectedDocument.procedure)
                : onOpenProcedure(selectedDocument.procedure, selectedDocument.id)}
            >
              {selectedFreshness === 'stale' ? '用当前数据新建配置' : '编辑设置 / 打开对应分析'}
            </button>
          </div>
        </section>
      ) : null}

      {documents.length ? (
        <section className="context-catalog" aria-label="项目分析对象">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">当前项目</p>
              <h2>分析与运行</h2>
            </div>
            <span className="status-badge">{documents.length} 项分析 · {runCount} 次运行</span>
          </div>

          <div className="method-catalog-filters">
            <label>
              搜索输出
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="分析名称、方法或运行 ID"
              />
            </label>
            <button type="button" className="secondary-button" disabled={!search} onClick={() => setSearch('')}>清除搜索</button>
          </div>
          <p className="catalog-result-count" role="status">显示 {filteredDocuments.length} / {documents.length} 项分析</p>

          {filteredDocuments.length ? (
            <div className="method-grid">
              {filteredDocuments.map((document) => {
                const runs = analysisRunsForDocument(index, document.id)
                const latestRun = runs[0]
                const latestFreshness = latestRun ? analysisRunFreshness(latestRun, dataset, measurement) : analysisDocumentFreshness(document, dataset, measurement)
                const latestDetail = latestRun ? detailsByRun.get(latestRun.id) : undefined
                const latestServerJob = latestRun ? serverJobsByRun.get(latestRun.id) : undefined
                const draft = latestFreshness === 'current'
                  ? empiricalDraftStatusForOutput(dataset, measurement, document.procedure, latestRun?.id, document.id)
                  : { dirtySinceLastRun: false, hasSavedDraft: false }
                return (
                  <article className="method-card" key={document.id}>
                    <div>
                      <p className="eyebrow">{document.categoryId.replaceAll('-', ' ')}</p>
                      <h3>{document.title}</h3>
                      <p>{runs.length} 次运行{latestRun ? ` · 最近 ${new Date(latestRun.createdAt).toLocaleString()}` : ''}</p>
                      <div className="method-card-status-row">
                        {document.pinned ? <span className="context-method-status">已固定</span> : null}
                        {document.primaryRunId ? <span className="context-method-status">已指定主要结果</span> : null}
                        <span className={`context-method-status${latestFreshness === 'stale' ? ' method-status-needs-setup' : ''}`}>
                          {latestFreshness === 'stale' ? '基于旧设置' : '当前数据/量表'}
                        </span>
                        {latestRun ? <span className="context-method-status">{runStatusLabel(latestServerJob?.status ?? latestDetail?.runStatus)}</span> : null}
                        {latestServerJob ? <span className="context-method-status">服务端已确认</span> : null}
                        {draft.dirtySinceLastRun ? <span className="context-method-status method-status-needs-setup">有未运行更改</span> : null}
                        {draft.hasSavedDraft ? <span className="context-method-status">草稿已保存</span> : null}
                      </div>
                      {latestDetail ? (
                        <p className="muted">运行 {latestDetail.runId.slice(0, 12)} · 草稿修订 {latestDetail.draftRevision} · {latestDetail.qualityStatus === 'warning' ? '含警告' : '无已记录警告'}</p>
                      ) : latestRun ? (
                        <p className="muted">最新运行 {latestRun.id.slice(0, 12)} · 仅有旧本地索引引用</p>
                      ) : null}
                    </div>

                    {runs.length ? (
                      <details>
                        <summary>查看运行历史</summary>
                        <ol>
                          {runs.map((run) => {
                            const detail = detailsByRun.get(run.id)
                            const serverJob = serverJobsByRun.get(run.id)
                            const freshness = analysisRunFreshness(run, dataset, measurement)
                            return (
                              <li key={run.id}>
                                <button type="button" className="text-button" onClick={() => setSelectedRunId(run.id)}>
                                  <code>{run.id.slice(0, 12)}</code>
                                  {' · '}{new Date(run.createdAt).toLocaleString()}
                                  {' · '}{runStatusLabel(serverJob?.status ?? detail?.runStatus)}
                                  {freshness === 'stale' ? ' · 基于旧设置' : ''}
                                  {document.primaryRunId === run.id ? ' · 主要结果' : ''}
                                  {detail ? ` · 修订 ${detail.draftRevision}` : ''}
                                  {serverJob ? ' · 服务端已确认' : ''}
                                </button>
                              </li>
                            )
                          })}
                        </ol>
                      </details>
                    ) : null}

                    <div className="method-card-actions">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => updateDocument(document.id, { pinned: !document.pinned })}
                      >
                        {document.pinned ? '取消固定' : '固定分析'}
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => {
                          const nextTitle = window.prompt('分析名称', document.title)
                          if (nextTitle !== null) updateDocument(document.id, { title: nextTitle })
                        }}
                      >
                        重命名
                      </button>
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => latestFreshness === 'stale'
                          ? onOpenProcedure(document.procedure)
                          : onOpenProcedure(document.procedure, document.id)}
                      >
                        {latestFreshness === 'stale' ? '用当前数据新建配置' : '编辑设置 / 打开当前结果'}
                      </button>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : (
            <div className="centered-state">
              <h3>没有匹配的输出</h3>
              <p>可以按分析名称、方法 ID、procedure 或运行 ID 搜索。</p>
            </div>
          )}
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
