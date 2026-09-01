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
    { caption: 'Reliability by construct', rows: asRows(reliability?.constructs) },
    { caption: 'Structural missingness', rows: objectValueRows(reliability?.structuralMissingness, 'constructId') },
    { caption: 'EFA factor-selection diagnostics', rows: [
      ...metricRows(efa?.map),
      ...metricRows(efa?.parallelAnalysis),
      ...metricRows(efa?.splitValidation),
    ] },
    { caption: 'EFA loadings', rows: asRows(efa?.loadings) },
    { caption: 'CFA fit indices', rows: cfa ? metricRows({
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
    { caption: 'CFA standardized loadings', rows: alignedRows(cfa?.itemIds, cfa?.standardizedLoadings, 'standardizedLoading') },
    { caption: 'Measurement invariance models', rows: objectValueRows(invariance?.models) },
    { caption: 'Measurement invariance comparisons', rows: objectValueRows(invariance?.comparisons) },
    { caption: 'Latent means', rows: asRows(invariance?.latentMeans) },
    { caption: 'Partial-invariance diagnostics', rows: asRows(invariance?.partialReleasedParameters) },
    { caption: 'Bifactor fit indices', rows: metricRows(bifactor?.fitIndices) },
    { caption: 'Bifactor indices', rows: metricRows(bifactor?.bifactorMetrics) },
    { caption: 'Bifactor item details', rows: asRows(bifactor?.itemDetails) },
    { caption: 'ESEM loadings', rows: asRows(esem?.loadings) },
    { caption: 'IRT item parameters', rows: asRows(irt?.itemParameters) },
    { caption: 'IRT DIF diagnostics', rows: asRows(irt?.difAnalysis) },
    { caption: 'Marker-variable CMB diagnostics', rows: marker ? metricRows({
      method: marker.method,
      markerVariableId: marker.markerVariableId,
      r_m: marker.r_m,
      sampleSize: marker.sampleSize,
      methodologicalWarning: marker.methodologicalWarning,
    }) : [] },
    { caption: 'ULMC model comparison', rows: ulmc ? [
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
        { caption: 'Omnibus tests', rows: asRows(familyResult.omnibusTests) },
        { caption: 'Estimated marginal means', rows: asRows(familyResult.estimatedMarginalMeans) },
        { caption: 'Contrasts', rows: asRows(familyResult.contrasts) },
        { caption: 'Planned contrasts', rows: asRows(familyResult.plannedContrasts) },
        { caption: 'Sphericity tests', rows: asRows(sphericity?.tests) },
        { caption: 'Sphericity corrections', rows: asRows(sphericity?.corrections) },
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
        { caption: 'Imputation convergence', rows: asRows(familyResult.convergence) },
        { caption: 'Missing information', rows: asRows(familyResult.missingInformation) },
        { caption: 'Derived datasets', rows: asRows(familyResult.artifacts) },
        { caption: 'Imputation trace', rows: asRows(familyResult.trace) },
        { caption: 'Imputed distributions', rows: asRows(familyResult.distribution) },
        { caption: 'Fraction of missing information', rows: asRows(familyResult.fractionMissingInformation) },
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
