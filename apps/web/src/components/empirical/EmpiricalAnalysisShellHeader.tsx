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
  const description = !measurement ? '直接选择原始变量进行当前分析；只有本方法需要量表时才补充量表设置。' : researchParadigm === 'longitudinal'
    ? `基于测量版本 v${measurement.version} 配置当前纵向方法所需的波次、变量和参数。`
    : researchParadigm === 'diary'
      ? `基于测量版本 v${measurement.version} 配置当前日记/ESM 方法需要的时间结构、中心化和变量。`
      : `基于测量版本 v${measurement.version} 配置当前方法需要的变量与参数。`
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
      <header className="analysis-shell-header">
        <div>
          <p className="eyebrow">分析配置</p>
          <h1>{method.label}</h1>
          <p className="muted">{description}</p>
        </div>
        <span className="status-chip">{measurement ? `${scores.length} 个构念 · N=${measurement.derivedDataset.rowCount}` : '原始变量'}</span>
      </header>
      <EmpiricalAnalysisConfig />
    </>
  )
}
