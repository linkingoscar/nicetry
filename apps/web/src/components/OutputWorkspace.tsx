import { useEffect, useMemo, useState } from 'react'

import type { DatasetVersion, MeasurementVersion } from '../types'
import type { EmpiricalProcedure } from '../types/empirical-types'
import { OutputEmpiricalRunPreview } from './OutputEmpiricalRunPreview'
import { empiricalDraftStatusForOutput } from './analyses/analysisDraftStatus'
import {
  analysisDocumentFreshness,
  analysisDocumentsForProject,
  analysisRunFreshness,
  analysisRunsForDocument,
  createEmpiricalAnalysisDocument,
  loadEmpiricalAnalysisIndex,
  setAnalysisPrimaryRun,
  updateAnalysisDocumentMetadata,
} from './analyses/analysisDocuments'
import { readAnalysisRunDetails } from './analyses/analysisRunDetails'
import {
  readRegisteredOutputRuns,
  registeredOutputFreshness,
} from './analyses/outputRunRegistry'
import { useOutputRunJobs } from './analyses/useOutputRunJobs'
import { cloneEmpiricalDraftsToAnalysis } from './empirical/empiricalDrafts'

interface OutputWorkspaceProps {
  dataset: DatasetVersion
  measurement: MeasurementVersion | null
  onOpenProcedure: (procedure: EmpiricalProcedure, analysisId?: string, runId?: string) => void
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

function registeredSourceLabel(source: 'model' | 'advanced', methodId: string) {
  if (source === 'model') return methodId === 'model.sem' ? 'SEM' : 'PROCESS / 模型'
  return '高级 / 结构化分析'
}

export function OutputWorkspace({ dataset, measurement, onOpenProcedure }: OutputWorkspaceProps) {
  const [index, setIndex] = useState(() => loadEmpiricalAnalysisIndex(dataset, measurement))
  const [registeredRuns, setRegisteredRuns] = useState(() => readRegisteredOutputRuns(dataset.projectId))
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    setIndex(loadEmpiricalAnalysisIndex(dataset, measurement))
    setRegisteredRuns(readRegisteredOutputRuns(dataset.projectId))
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
  const filteredRegisteredRuns = useMemo(() => registeredRuns.filter((run) => {
    if (!normalizedSearch) return true
    return `${run.label} ${run.methodId} ${run.runId} ${run.family ?? ''} ${run.modelId ?? ''}`
      .toLocaleLowerCase()
      .includes(normalizedSearch)
  }), [normalizedSearch, registeredRuns])

  const allRuns = documents.flatMap((document) => analysisRunsForDocument(index, document.id))
  const currentRunIds = allRuns
    .filter((run) => analysisRunFreshness(run, dataset, measurement) === 'current')
    .map((run) => run.id)
  const serverJobsByRun = useOutputRunJobs(currentRunIds, dataset.id, measurement?.version ?? null)
  const runCount = allRuns.length
  const totalOutputCount = documents.length + registeredRuns.length
  const filteredOutputCount = filteredDocuments.length + filteredRegisteredRuns.length

  const selectedRun = selectedRunId ? index.runs.find((run) => run.id === selectedRunId) : undefined
  const selectedDocument = selectedRun ? documents.find((document) => document.id === selectedRun.analysisId) : undefined
  const selectedDetail = selectedRun ? detailsByRun.get(selectedRun.id) : undefined
  const selectedServerJob = selectedRun ? serverJobsByRun.get(selectedRun.id) : undefined
  const selectedFreshness = selectedRun ? analysisRunFreshness(selectedRun, dataset, measurement) : undefined
  const selectedStatus = selectedServerJob?.status ?? selectedDetail?.runStatus
  const selectedReportId = selectedServerJob?.reportId ?? selectedDetail?.resultId ?? undefined
  const selectedOptions = selectedServerJob?.options ?? selectedDetail?.submittedSpec

  const updateDocument = (analysisId: string, patch: { title?: string; pinned?: boolean }) => {
    setIndex(updateAnalysisDocumentMetadata(dataset.projectId, analysisId, patch))
  }
  const updatePrimaryRun = (analysisId: string, runId: string | null) => {
    setIndex(setAnalysisPrimaryRun(dataset.projectId, analysisId, runId))
  }
  const duplicateDocument = (document: (typeof documents)[number]) => {
    if (analysisDocumentFreshness(document, dataset, measurement) !== 'current') return
    const duplicate = createEmpiricalAnalysisDocument(
      dataset,
      measurement,
      document.procedure,
      `${document.title} 副本`,
    )
    cloneEmpiricalDraftsToAnalysis(
      dataset,
      measurement,
      document.id,
      duplicate.id,
      document.procedure,
    )
    setIndex(loadEmpiricalAnalysisIndex(dataset, measurement))
    onOpenProcedure(duplicate.procedure, duplicate.id)
  }

  return (
    <main className="analysis-shell" aria-labelledby="output-workspace-heading">
      <header className="analysis-shell-header">
        <div>
          <p className="eyebrow">分析对象与运行</p>
          <h1 id="output-workspace-heading">输出</h1>
          <p>统一查看当前项目的实证、PROCESS/SEM 与结构化高级分析。旧数据或量表版本的结果继续可见，并明确标记为“基于旧设置”。</p>
        </div>
      </header>

      {totalOutputCount ? (
        <section className="context-catalog" aria-label="项目输出索引">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">当前项目</p>
              <h2>输出索引</h2>
            </div>
            <span className="status-badge">{documents.length} 项实证分析 · {registeredRuns.length} 个模型/高级运行</span>
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
          <p className="catalog-result-count" role="status">显示 {filteredOutputCount} / {totalOutputCount} 项输出</p>
        </section>
      ) : null}

      {selectedRun && selectedDocument ? (
        <section className="context-catalog" aria-label="选中的运行">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">当前运行</p>
              <h2>{selectedDocument.title}</h2>
              <p className="muted">{new Date(selectedRun.createdAt).toLocaleString()} · {runStatusLabel(selectedStatus)}</p>
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

          {selectedFreshness === 'current' && selectedStatus === 'succeeded' && selectedReportId && selectedOptions ? (
            <OutputEmpiricalRunPreview
              datasetId={dataset.id}
              measurementVersion={measurement?.version ?? null}
              reportId={selectedReportId}
              options={selectedOptions}
            />
          ) : null}

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
                : onOpenProcedure(selectedDocument.procedure, selectedDocument.id, selectedRun.id)}
            >
              {selectedFreshness === 'stale' ? '用当前数据新建配置' : '打开该运行结果 / 设置'}
            </button>
          </div>
        </section>
      ) : null}

      {registeredRuns.length ? (
        <section className="context-catalog" aria-label="模型与高级运行">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">统一运行引用</p>
              <h2>PROCESS / SEM / 高级分析</h2>
              <p className="muted">这里只保存服务端 runId 与来源身份，不在浏览器中复制结果或伪造任务状态。</p>
            </div>
            <span className="status-badge">{registeredRuns.length} 个运行</span>
          </div>
          {filteredRegisteredRuns.length ? (
            <div className="method-grid">
              {filteredRegisteredRuns.map((run) => {
                const freshness = registeredOutputFreshness(run, dataset, measurement)
                return (
                  <article className="method-card" key={`${run.source}:${run.runId}`}>
                    <div>
                      <p className="eyebrow">{registeredSourceLabel(run.source, run.methodId)}</p>
                      <h3>{run.label}</h3>
                      <p>{new Date(run.createdAt).toLocaleString()}</p>
                      <div className="method-card-status-row">
                        <span className={`context-method-status${freshness === 'stale' ? ' method-status-needs-setup' : ''}`}>
                          {freshness === 'stale' ? '基于旧设置' : '当前数据/量表'}
                        </span>
                        <span className="context-method-status">运行引用</span>
                      </div>
                      <p className="muted">方法 {run.methodId} · run {run.runId.slice(0, 12)}</p>
                      <p className="muted">服务端状态和只读结果将在下一层按 runId 恢复；本地索引不声明任务成功或失败。</p>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : <p className="muted">当前搜索没有匹配的 PROCESS、SEM 或高级运行。</p>}
        </section>
      ) : null}

      {documents.length ? (
        <section className="context-catalog" aria-label="实证分析对象">
          <div className="section-heading-row">
            <div>
              <p className="eyebrow">实证分析对象</p>
              <h2>分析与运行</h2>
            </div>
            <span className="status-badge">{documents.length} 项分析 · {runCount} 次运行</span>
          </div>

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
                      {latestFreshness === 'current' ? (
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => duplicateDocument(document)}
                        >
                          复制分析
                        </button>
                      ) : null}
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
          ) : <p className="muted">当前搜索没有匹配的实证分析。</p>}
        </section>
      ) : null}

      {!totalOutputCount ? (
        <section className="centered-state">
          <h2>还没有运行任何分析</h2>
          <p>从“分析”选择一个方法并显式运行后，这里会记录分析对象或服务端运行引用。</p>
        </section>
      ) : null}
    </main>
  )
}
