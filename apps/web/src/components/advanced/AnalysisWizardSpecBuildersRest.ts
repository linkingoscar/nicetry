import type { AnalysisSpecBuilderContext } from './AnalysisWizard.templateTypes'

export function buildMultipleImputationSpec({
  base,
  sliceId,
  datasetId,
  variables,
  numericIds,
  template,
}: AnalysisSpecBuilderContext): object {
  const outcomeId = numericIds[0] ?? ''
  const predictorIds = numericIds.slice(1, 3)
  const modelVariableIds = [outcomeId, ...predictorIds].filter(Boolean)
  const imputationIds = variables
    .filter(variable => variable.type === 'numeric' && (variable.missingRate ?? 0) > 0)
    .map(variable => variable.id)
    .slice(0, 4)
  const selectedImputationIds = imputationIds.length > 0 ? imputationIds : numericIds.slice(0, 1)
  return template({
    ...base,
    family: 'multiple_imputation',
    datasetVersionId: datasetId ?? '',
    method: 'mice_fcs',
    imputations: 20,
    iterations: 20,
    variables: selectedImputationIds.map(variableId => ({
      variableId,
      method: 'auto',
      predictorIds: modelVariableIds.filter(id => id !== variableId),
    })),
    passiveRules: [],
    pooling: sliceId?.endsWith('.mice_dataset_generation') ? 'none' : 'rubin',
    ...(sliceId?.endsWith('.mice_dataset_generation') ? {} : {
      pooledAnalysis: {
        modelType: 'linear_regression',
        outcomeId,
        predictorIds,
        includeIntercept: true,
      },
    }),
    diagnostics: ['trace', 'distribution', 'fraction_missing_information'],
  })
}

export function buildMultilevelModelSpec({
  base,
  sliceId,
  datasetId,
  numericIds,
  categoricalIds,
  selectedItemIds,
  context,
  template,
}: AnalysisSpecBuilderContext): object {
  const contextClusterId = context?.structure?.roles.clusterId ?? ''
  const clusterVariableId = contextClusterId || categoricalIds[0] || ''
  const outcomeId = numericIds.find(id => id !== clusterVariableId) ?? numericIds[0] ?? null
  const fixedEffectIds = numericIds.filter(id => id !== clusterVariableId && id !== outcomeId).slice(0, 3)
  return template({
    ...base,
    family: 'multilevel_model',
    datasetVersionId: datasetId ?? '',
    analysisType: sliceId?.endsWith('.aggregation.icc_rwg') ? 'aggregation' : 'lmm',
    outcomeId: sliceId?.endsWith('.aggregation.icc_rwg') ? null : outcomeId,
    distribution: 'gaussian',
    clusterVariableId,
    fixedEffectIds: sliceId?.endsWith('.aggregation.icc_rwg') ? [] : fixedEffectIds,
    randomEffects: sliceId?.endsWith('.aggregation.icc_rwg') ? [] : clusterVariableId
      ? [{ groupingVariableId: clusterVariableId, intercept: true, slopeVariableIds: [], covariance: 'correlated' }]
      : [],
    centering: [],
    estimator: 'REML',
    degreesOfFreedom: 'satterthwaite',
    minimumClusterCount: 30,
    scaleItemIds: sliceId?.endsWith('.aggregation.icc_rwg') ? selectedItemIds.slice(0, 8) : selectedItemIds,
    scaleMin: 1,
    scaleMax: 5,
    aggregationMethod: 'mean',
  })
}

export function buildQuestionnaireMeasurementSpec({
  base,
  sliceId,
  datasetId,
  selectedItemIds,
  selectedConstructs,
  categoricalIds,
  numericIds,
  context,
  template,
}: AnalysisSpecBuilderContext): object {
  return template({
    ...base,
    family: 'questionnaire_measurement',
    datasetVersionId: datasetId ?? '',
    modelType: sliceId?.endsWith('.efa')
      ? 'efa'
      : sliceId?.endsWith('.cfa')
        ? 'cfa'
        : sliceId?.endsWith('.measurement_invariance')
          ? 'measurement_invariance'
          : sliceId?.endsWith('.esem_bifactor_irt')
            ? 'esem_bifactor_irt'
            : sliceId?.endsWith('.common_method_bias')
              ? 'common_method_bias'
              : 'reliability',
    itemIds: selectedItemIds,
    constructs: selectedConstructs,
    groupVariableId: sliceId?.endsWith('.measurement_invariance')
      ? context?.structure?.roles?.groupId ?? categoricalIds[0]
      : undefined,
    markerVariableId: sliceId?.endsWith('.common_method_bias')
      ? categoricalIds[0] ?? numericIds.at(-1)
      : undefined,
    estimator: 'ML',
    itemScale: 'continuous',
    factorCount: 2,
    rotation: sliceId?.endsWith('.esem_bifactor_irt') ? 'target' : 'promax',
    irtModel: 'auto',
    parallelIterations: 1000,
    invarianceLevels: ['configural', 'metric', 'scalar'],
  })
}
