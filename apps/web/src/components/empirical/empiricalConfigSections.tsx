import { useEmpiricalAnalysisContext } from './EmpiricalAnalysisContext'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import { EmpiricalRegressionSection } from './empiricalConfigRegressionSection'

export function EmpiricalAnalysisCoreSections() {
  const {
    researchParadigm,
    nestedContext,
  } = useEmpiricalAnalysisContext()
  const showCrossSectional = researchParadigm === 'questionnaire'
  const showLongitudinal = researchParadigm === 'longitudinal'

  return (
    <>
      {showCrossSectional && !nestedContext ? (
      <div className="analysis-config-flow-heading">
        <div>
          <strong>横截面基础流程</strong>
          <span>按论文分析顺序完成样本、测量和回归设置</span>
        </div>
        <small>常用</small>
      </div>
      ) : showCrossSectional ? (
        <div className="analysis-config-flow-heading is-advanced">
          <div>
            <strong>嵌套设计推断边界</strong>
            <span>本页只运行描述、测量准备和聚合诊断；组间比较、单层回归与响应面需使用 cluster-aware 或多层规格。</span>
          </div>
          <small>已阻断不适用方法</small>
        </div>
      ) : null}
      {showCrossSectional ? (
        <CrossSectionalBasicSection />
      ) : (
        <RepeatedMeasuresSampleSection />
      )}
      {showCrossSectional || showLongitudinal ? (
        <MeasurementModelSection />
      ) : null}
      {showCrossSectional && !nestedContext ? (
        <EmpiricalRegressionSection />
      ) : null}
    </>
  )
}

function CrossSectionalBasicSection() {
  const {
    config: value,
    onConfigChange: onChange,
    nestedContext,
    groupCandidates,
    aggregationCandidates,
    contextRoles,
    sampleVersions,
  } = useEmpiricalAnalysisContext()

  return (
    <details className="analysis-config-section" open>
      <summary><span>1</span><strong>基础分析与样本</strong><small>相关方法、分析样本和分组变量</small></summary>
      <div className="empirical-config-grid">
        <label>相关分析方法
          <select value={value.correlationMethod} onChange={(event) => onChange({ correlationMethod: event.target.value as EmpiricalConfigValue['correlationMethod'] })}>
            <option value="pearson">Pearson 相关（积差）</option>
            <option value="spearman">Spearman 秩相关</option>
            <option value="partial">偏相关（基于控制变量）</option>
          </select>
        </label>
        <label>相关矩阵多重校正
          <select disabled={nestedContext} value={value.correlationPAdjust} onChange={(event) => onChange({ correlationPAdjust: event.target.value as EmpiricalConfigValue['correlationPAdjust'] })}>
            <option value="BH">BH/FDR（探索性默认）</option>
            <option value="holm">Holm（控制 FWER）</option>
            <option value="none">不校正（必须按原始 p 报告）</option>
          </select>
        </label>
        <label>跨构念 omnibus 校正
          <select disabled={nestedContext} value={value.groupOmnibusPAdjust} onChange={(event) => onChange({ groupOmnibusPAdjust: event.target.value as EmpiricalConfigValue['groupOmnibusPAdjust'] })}>
            <option value="holm">Holm（默认）</option>
            <option value="BH">BH/FDR</option>
            <option value="none">不校正（必须披露）</option>
          </select>
        </label>
        <label>主推断统一 family 校正
          <select disabled={nestedContext} value={value.multiplicityPAdjust} onChange={(event) => onChange({ multiplicityPAdjust: event.target.value as EmpiricalConfigValue['multiplicityPAdjust'] })}>
            <option value="BH">BH/FDR</option>
            <option value="holm">Holm（FWER）</option>
            <option value="none">不校正（必须披露）</option>
          </select>
        </label>
        <label>置信水平
          <select value={value.confidenceLevel} onChange={(event) => onChange({ confidenceLevel: Number(event.target.value) })}>
            <option value={0.9}>90%</option>
            <option value={0.95}>95%</option>
            <option value={0.99}>99%</option>
          </select>
        </label>
        <label>统一多重性家族 ID
          <input value={value.multiplicityFamilyId} onChange={(event) => onChange({ multiplicityFamilyId: event.target.value })} />
        </label>
        <label>分析样本版本（可选）
          <select value={value.sampleVersionId ?? ''} onChange={(event) => onChange({ sampleVersionId: event.target.value || null })}>
            <option value="">使用测量版本全部案例</option>
            {sampleVersions?.map((sample) => (
              <option key={sample.id} value={sample.id}>{sample.label} · 纳入 {sample.includedCount} · {sample.sampleHash.slice(0, 10)}</option>
            ))}
          </select>
        </label>
        <label>组间差异变量（可选）
          <select disabled={nestedContext} value={value.groupVariableId ?? ''} onChange={(event) => onChange({ groupVariableId: event.target.value || null })}>
            <option value="">不进行组间差异检验</option>
            {groupCandidates.map((variable) => <option key={variable.id} value={variable.id}>{variable.label}</option>)}
          </select>
        </label>
        {contextRoles?.clusterId ? (
          <label>cluster 聚合变量
            <select value={value.aggregationVariableId ?? ''} onChange={(event) => onChange({ aggregationVariableId: event.target.value || null })}>
              <option value="">不运行聚合诊断</option>
              {aggregationCandidates.map((variable) => <option key={variable.id} value={variable.id}>{variable.label}</option>)}
            </select>
          </label>
        ) : null}
      </div>
      {nestedContext ? <p className="method-note">当前为 nested 横截面：相关系数只作描述，普通逐行 p 值/区间、组间检验和单层回归不会执行。请在这里选择：先报告聚合证据；进入两层 Gaussian LMM；或仅保留描述性结果。</p> : null}
    </details>
  )
}

function RepeatedMeasuresSampleSection() {
  const { config: value, onConfigChange: onChange, sampleVersions } = useEmpiricalAnalysisContext()

  return (
    <details className="analysis-config-section" open>
      <summary><span>1</span><strong>样本与重复测量边界</strong><small>固定分析样本、个体与时间结构</small></summary>
      <div className="empirical-config-grid">
        <label>分析样本版本（可选）
          <select value={value.sampleVersionId ?? ''} onChange={(event) => onChange({ sampleVersionId: event.target.value || null })}>
            <option value="">使用测量版本全部案例</option>
            {sampleVersions?.map((sample) => (
              <option key={sample.id} value={sample.id}>{sample.label} · 纳入 {sample.includedCount} · {sample.sampleHash.slice(0, 10)}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="method-note">当前为重复测量工作流：不提供横截面组间、单层回归、响应面或逐行相关显著性设置；描述与测量准备不生成 IID p 值/区间，正式推断只来自下方显式选择的纵向或多层模型。</p>
    </details>
  )
}

export function MeasurementModelSection() {
  const {
    config: value,
    onConfigChange: onChange,
    researchParadigm,
  } = useEmpiricalAnalysisContext()
  const showCrossSectional = researchParadigm === 'questionnaire'

  return (
    <details className="analysis-config-section">
      <summary><strong>因子提取与旋转</strong><small>仅设置 EFA</small></summary>
      <div className="empirical-config-grid">
        <label>EFA 旋转方法
          <select value={value.rotation} onChange={(event) => onChange({ rotation: event.target.value as EmpiricalConfigValue['rotation'] })}>
            <option value="varimax">Varimax 正交旋转</option>
            <option value="promax">Promax 斜交旋转</option>
          </select>
        </label>
        <label>因子保留方法
          <select value={value.factorCountMethod} onChange={(event) => onChange({ factorCountMethod: event.target.value as EmpiricalConfigValue['factorCountMethod'] })}>
            <option value="kaiser">Kaiser 准则（特征值 &gt; 1.0）</option>
            <option value="parallel_analysis">Parallel Analysis 平行分析</option>
            <option value="manual">手动指定因子数</option>
          </select>
        </label>
        {value.factorCountMethod === 'manual' ? (
          <label>探索性因子数
            <input type="number" min="1" max="20" value={value.factorCount} onChange={(event) => onChange({ factorCount: Number(event.target.value) })} />
          </label>
        ) : null}
        {value.factorCountMethod === 'parallel_analysis' ? (
          <>
            <label>平行分析模拟次数
              <input type="number" min="100" max="10000" step="100" value={value.parallelIterations} onChange={(event) => onChange({ parallelIterations: Number(event.target.value) })} />
            </label>
            <label>随机种子
              <input type="number" min="1" value={value.randomSeed} onChange={(event) => onChange({ randomSeed: Number(event.target.value) })} />
            </label>
          </>
        ) : null}
      </div>
      <p className="method-note">{showCrossSectional
        ? '只执行当前所选的探索性因子分析。CFA、效度、多组等值性与共同方法偏差诊断需在方法菜单中分别选择。'
        : '这里的 EFA/CFA 只作纵向测量准备；当前基础链路不执行纵向测量等值性推断，也不把普通逐行拟合解释为正式纵向测量证据。'}</p>
    </details>
  )
}
