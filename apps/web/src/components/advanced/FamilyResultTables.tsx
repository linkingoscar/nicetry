import { ResultDataTable } from './ResultDataTable'

interface FamilyResultTablesProps {
  familyResult: Record<string, unknown>
}

interface TableDefinition {
  caption: string
  rows: Array<Record<string, unknown>>
}

function asRows(value: unknown): Array<Record<string, unknown>> {
  if (!Array.isArray(value)) return []
  return value.filter(
    (item): item is Record<string, unknown> => item !== null && typeof item === 'object' && !Array.isArray(item),
  )
}

function metricRows(value: unknown): Array<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.entries(value).map(([metric, result]) => ({ metric, value: result }))
}

function objectValueRows(value: unknown, key = 'level'): Array<Record<string, unknown>> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  return Object.entries(value).flatMap(([label, result]) => {
    if (result && typeof result === 'object' && !Array.isArray(result)) {
      return [{ [key]: label, ...(result as Record<string, unknown>) }]
    }
    return [{ [key]: label, value: result }]
  })
}

function alignedRows(ids: unknown, values: unknown, valueKey: string): Array<Record<string, unknown>> {
  if (!Array.isArray(ids) || !Array.isArray(values)) return []
  return ids.map((itemId, index) => ({ itemId, [valueKey]: values[index] }))
}

function questionnaireDefinitions(familyResult: Record<string, unknown>): TableDefinition[] {
  const reliability = familyResult.reliability as Record<string, unknown> | null
  const efa = familyResult.efa as Record<string, unknown> | null
  const cfa = familyResult.cfa as Record<string, unknown> | null
  const invariance = familyResult.invariance as Record<string, unknown> | null
  const bifactor = familyResult.bifactor as Record<string, unknown> | null
  const esem = familyResult.esem as Record<string, unknown> | null
  const irt = familyResult.irt as Record<string, unknown> | null
  const cmb = familyResult.commonMethodBias as Record<string, unknown> | null
  const marker = cmb?.markerVariable as Record<string, unknown> | null
  const ulmc = cmb?.ulmc as Record<string, unknown> | null

  return [
    { caption: '分构念信度', rows: asRows(reliability?.constructs) },
    { caption: '结构性缺失', rows: objectValueRows(reliability?.structuralMissingness, 'constructId') },
    { caption: 'EFA 因子保留诊断', rows: [
      ...metricRows(efa?.map),
      ...metricRows(efa?.parallelAnalysis),
      ...metricRows(efa?.splitValidation),
    ] },
    { caption: 'EFA 因子载荷', rows: asRows(efa?.loadings) },
    { caption: 'CFA 拟合指标', rows: cfa ? metricRows({
      chiSquare: cfa.chiSquare,
      degreesOfFreedom: cfa.degreesOfFreedom,
      pValue: cfa.pValue,
      cfi: cfa.cfi,
      tli: cfa.tli,
      rmsea: cfa.rmsea,
      rmseaCiLower: cfa.rmseaCiLower,
      rmseaCiUpper: cfa.rmseaCiUpper,
      srmr: cfa.srmr,
      estimator: cfa.estimator,
      hasHeywoodCase: cfa.hasHeywoodCase,
    }) : [] },
    { caption: 'CFA 方法执行', rows: metricRows(cfa?.methodExecution) },
    { caption: 'CFA 标准化载荷', rows: alignedRows(cfa?.itemIds, cfa?.standardizedLoadings, 'standardizedLoading') },
    { caption: '测量等值性模型', rows: objectValueRows(invariance?.models) },
    { caption: '测量等值性比较', rows: objectValueRows(invariance?.comparisons) },
    { caption: '潜变量均值', rows: asRows(invariance?.latentMeans) },
    { caption: '部分等值性诊断', rows: asRows(invariance?.partialReleasedParameters) },
    { caption: 'Bifactor 拟合指标', rows: metricRows(bifactor?.fitIndices) },
    { caption: 'Bifactor 方法执行', rows: metricRows(bifactor?.methodExecution) },
    { caption: 'Bifactor 辅助指标', rows: metricRows(bifactor?.bifactorMetrics) },
    { caption: 'Bifactor 题项详情', rows: asRows(bifactor?.itemDetails) },
    { caption: 'ESEM 因子载荷', rows: asRows(esem?.loadings) },
    { caption: 'ESEM 方法执行', rows: metricRows(esem?.methodExecution) },
    { caption: 'IRT 题项参数', rows: asRows(irt?.itemParameters) },
    { caption: 'IRT 方法执行', rows: metricRows(irt?.methodExecution) },
    { caption: 'IRT DIF 诊断', rows: asRows(irt?.difAnalysis) },
    { caption: 'Marker Variable 共同方法偏差诊断', rows: marker ? metricRows({
      method: marker.method,
      markerVariableId: marker.markerVariableId,
      r_m: marker.r_m,
      sampleSize: marker.sampleSize,
      methodologicalWarning: marker.methodologicalWarning,
    }) : [] },
    { caption: 'ULMC 模型比较', rows: ulmc ? [
      ...metricRows(ulmc.baselineModel),
      ...metricRows(ulmc.ulmcModel),
      ...metricRows(ulmc.modelComparison),
    ] : [] },
  ]
}

function definitionsFor(familyResult: Record<string, unknown>): TableDefinition[] {
  switch (familyResult.family) {
    case 'questionnaire_measurement':
      return questionnaireDefinitions(familyResult)
    case 'experimental_design': {
      const sphericity = familyResult.sphericity && typeof familyResult.sphericity === 'object'
        ? familyResult.sphericity as Record<string, unknown>
        : null
      return [
        { caption: '总体效应检验', rows: asRows(familyResult.omnibusTests) },
        { caption: '估计边际均值', rows: asRows(familyResult.estimatedMarginalMeans) },
        { caption: '事后对比', rows: asRows(familyResult.contrasts) },
        { caption: '计划对比', rows: asRows(familyResult.plannedContrasts) },
        { caption: '球形性检验', rows: asRows(sphericity?.tests) },
        { caption: '球形性校正', rows: asRows(sphericity?.corrections) },
      ]
    }
    case 'multilevel_model':
      return [
        { caption: 'Fixed effects', rows: asRows(familyResult.fixedEffects) },
        { caption: 'Random effects', rows: asRows(familyResult.randomEffects) },
        { caption: 'Variance components', rows: asRows(familyResult.varianceComponents) },
        { caption: 'ICC', rows: asRows(familyResult.icc) },
        { caption: 'Fit indices', rows: metricRows(familyResult.fitIndices) },
      ]
    case 'longitudinal_model':
      {
        const invariance = familyResult.invariance && typeof familyResult.invariance === 'object'
          ? familyResult.invariance as Record<string, unknown>
          : null
        return [
          { caption: 'Longitudinal parameters', rows: asRows(familyResult.parameters) },
          { caption: 'Wave sample flow', rows: asRows(familyResult.waveSampleFlow) },
          { caption: 'Fit indices', rows: metricRows(familyResult.fitIndices) },
          { caption: 'Invariance models', rows: objectValueRows(invariance?.models) },
          { caption: 'Invariance comparisons', rows: objectValueRows(invariance?.comparisons) },
          { caption: 'Longitudinal latent means', rows: asRows(invariance?.latentMeans) },
          { caption: 'Missing-pattern evidence', rows: familyResult.missingPatterns ? [{ pattern: familyResult.missingPatterns }] : [] },
        ]
      }
    case 'multiple_imputation':
      return [
        { caption: '插补链收敛', rows: asRows(familyResult.convergence) },
        { caption: '缺失信息', rows: asRows(familyResult.missingInformation) },
        { caption: '派生插补数据集', rows: asRows(familyResult.artifacts) },
        { caption: '插补迭代轨迹', rows: asRows(familyResult.trace) },
        { caption: '插补前后分布', rows: asRows(familyResult.distribution) },
        { caption: '缺失信息比例', rows: asRows(familyResult.fractionMissingInformation) },
      ]
    default:
      return []
  }
}

export function FamilyResultTables({ familyResult }: FamilyResultTablesProps) {
  const definitions = definitionsFor(familyResult).filter(({ rows }) => rows.length > 0)
  if (definitions.length === 0) return null

  return (
    <section className="adv-result-section" aria-label="Family-specific results">
      <h3>方法专用结果</h3>
      {definitions.map(({ caption, rows }) => (
        <ResultDataTable key={caption} caption={caption} rows={rows} />
      ))}
    </section>
  )
}
