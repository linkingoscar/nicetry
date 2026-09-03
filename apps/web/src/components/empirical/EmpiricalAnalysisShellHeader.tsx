import { EmpiricalAnalysisConfig } from './EmpiricalAnalysisConfig'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import { procedureDefinition } from './empiricalProcedures'

export function EmpiricalAnalysisShellHeader() {
  const {
    measurement,
    scores,
    researchParadigm,
    config,
    activeRunId,
    analysisJob,
    isConfigStale,
    isRunning,
  } = useEmpiricalAnalysisContext()
  const description = !measurement ? '直接选择原始变量进行分析，无需建立构念；量表分析需先完成测量配置。' : researchParadigm === 'longitudinal'
    ? `基于测量版本 v${measurement.version} 配置波次、等值性与纵向动态模型。`
    : researchParadigm === 'diary'
      ? `基于测量版本 v${measurement.version} 检查时间结构、中心化与个体内/个体间效应。`
      : `基于测量版本 v${measurement.version} 选择需要的分析、指定变量后单独运行。`
  const method = procedureDefinition(config.procedure)
  const draftStatus = isRunning
    ? `运行中${activeRunId ? ` · ${activeRunId.slice(0, 12)}` : ''}`
    : activeRunId && isConfigStale
      ? `有未运行更改 · 当前结果 ${activeRunId.slice(0, 12)}`
      : activeRunId
        ? `当前设置对应运行 ${activeRunId.slice(0, 12)}`
        : '草稿 · 尚未运行'

  return (
    <>
      <section className="method-note" aria-label="当前分析对象">
        <strong>{method.label}</strong>
        <span> · {draftStatus}</span>
        {analysisJob?.status === 'failed' ? <span> · 最近运行失败，历史结果未被覆盖</span> : null}
      </section>
      <header className="empirical-hero">
        <div>
          <p className="eyebrow">实证证据中心</p>
          <h1>{researchParadigm === 'longitudinal' ? '纵向面板分析中心' : researchParadigm === 'diary' ? '日记与 ESM 分析中心' : '问卷实证分析中心'}</h1>
          <p className="muted">{description}</p>
          <div className="analysis-inline-actions empirical-demo-links">
            <a className="secondary-button" href="/api/v1/demo/data/longitudinal" download>
              下载五波 RI-CLPM 示例
            </a>
            <a className="secondary-button" href="/api/v1/demo/data/diary" download>
              下载日记 MLM 示例
            </a>
            <a className="secondary-button" href="/api/v1/demo/data/esm" download>
              下载 ESM / GLMM 示例
            </a>
          </div>
        </div>
        <span className="status-chip">{measurement ? `${scores.length} 个构念 · N=${measurement.derivedDataset.rowCount}` : '原始变量 · 无测量版本'}</span>
      </header>
      <EmpiricalAnalysisConfig />
    </>
  )
}
