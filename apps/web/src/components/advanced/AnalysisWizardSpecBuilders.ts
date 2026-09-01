import type { AnalysisSpecBuilderContext } from './AnalysisWizard.templateTypes'

export function buildPowerAnalysisSpec({
  base,
  sliceId,
  template,
}: AnalysisSpecBuilderContext): object {
  return template({
    ...base,
    family: 'power_analysis',
    designFamily: sliceId?.endsWith('.t_test')
      ? 't_test'
      : sliceId?.endsWith('.factorial_anova')
        ? 'factorial_anova'
        : 'regression',
    method: sliceId === 'power_analysis.monte_carlo' ? 'monte_carlo' : 'analytic',
    solveFor: 'sample_size',
    alpha: 0.05,
    targetPower: 0.8,
    effectSize: {
      metric: sliceId?.endsWith('.t_test')
        ? 'cohens_d'
        : sliceId?.endsWith('.factorial_anova')
          ? 'cohens_f'
          : 'cohens_f2',
      value: 0.15,
    },
    effectSizeMetric: sliceId?.endsWith('.t_test')
      ? 'cohens_d'
      : sliceId?.endsWith('.factorial_anova')
        ? 'cohens_f'
        : 'cohens_f2',
    predictors: sliceId?.endsWith('.t_test') ? 1 : 3,
    groups: sliceId?.endsWith('.t_test') || sliceId?.endsWith('.factorial_anova') ? 2 : 1,
    simulations: 5000,
    alternative: 'two_sided',
    roundingRule: 'ceil',
    ...(sliceId === 'power_analysis.monte_carlo' ? {
      monteCarloParameters: {
        dataGeneration: { model: 'regression', sampleSize: 200, coefficients: [0.3] },
        estimandTarget: 'beta_1',
        convergenceFailureHandling: 'drop',
      },
    } : {}),
  })
}

export function buildExperimentalDesignSpec({
  base,
  sliceId,
  datasetId,
  numericIds,
  categoricalIds,
  context,
  template,
}: AnalysisSpecBuilderContext): object {
  const designType = sliceId?.includes('.ancova.')
    ? 'ancova'
    : sliceId?.includes('.repeated_measures.')
      ? 'repeated_measures'
      : sliceId?.includes('.mixed_design.')
        ? 'mixed_design'
        : 'factorial_anova'
  const outcomeId = numericIds[0] ?? ''
  const treatmentId = context?.structure?.roles?.treatmentId
    ?? context?.structure?.roles?.groupId
    ?? categoricalIds[0]
  const subjectId = context?.structure?.roles?.subjectId ?? ''
  const betweenFactors = treatmentId ? [{ variableId: treatmentId, coding: 'sum' }] : []
  const repeatedDesign = ['repeated_measures', 'mixed_design'].includes(designType)
  const widePanel = context?.structure?.roles?.dataLayout === 'wide'
  const withinVariableIds = numericIds.slice(0, 2)
  const withinLevels = withinVariableIds.length >= 2
    ? withinVariableIds.map((_, index) => String(index + 1))
    : ['1', '2']
  const withinColumns = widePanel && withinVariableIds.length >= 2
    ? Object.fromEntries(withinLevels.map((level, index) => [level, withinVariableIds[index]]))
    : {}
  return template({
    ...base,
    family: 'experimental_design',
    analysisType: sliceId?.includes('.glm_cluster.') ? 'glm_cluster' : 'anova',
    designType,
    dataLayout: repeatedDesign && widePanel ? 'wide' : 'long',
    datasetVersionId: datasetId ?? '',
    outcomeIds: outcomeId ? [outcomeId] : [],
    betweenFactors: designType === 'repeated_measures' ? [] : betweenFactors,
    withinFactors: repeatedDesign
      ? [{ id: 'time', name: '时间', levels: withinLevels.length >= 2 ? withinLevels : ['1', '2'], columns: withinColumns }]
      : [],
    subjectId: repeatedDesign ? subjectId : undefined,
    covariateIds: designType === 'ancova'
      ? numericIds.filter(id => id !== outcomeId).slice(0, 1)
      : [],
    clusterVariableId: sliceId?.includes('.glm_cluster.')
      ? (context?.structure?.roles?.clusterId ?? categoricalIds[0])
      : undefined,
    sumOfSquares: 'III',
    postHocAdjustment: 'holm',
  })
}
