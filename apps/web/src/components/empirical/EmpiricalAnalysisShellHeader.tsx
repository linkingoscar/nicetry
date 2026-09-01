import { EmpiricalAnalysisConfig } from './EmpiricalAnalysisConfig'
import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'

export function EmpiricalAnalysisShellHeader() {
  const { measurement, scores, researchParadigm } = useEmpiricalAnalysisContext()
  const description = !measurement ? '直接选择原始变量进行分析，无需建立构念；量表分析需先完成测量配置。' : researchParadigm === 'longitudinal'
    ? `基于测量版本 v${measurement.version} 配置波次、等值性与纵向动态模型。`
    : researchParadigm === 'diary'
      ? `基于测量版本 v${measurement.version} 检查时间结构、中心化与个体内/个体间效应。`
      : `基于测量版本 v${measurement.version} 选择需要的分析、指定变量后单独运行。`
  return (
    <>
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
