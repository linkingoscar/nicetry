import type {
  DatasetVersion,
  EmpiricalAnalysisOptions,
  MeasurementVersion,
} from '../../types'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { EmpiricalConfigValue } from './EmpiricalAnalysisConfig'

export interface EmpiricalDerivedState {
  scores: MeasurementVersion['derivedDataset']['scoreVariables']
  groupCandidates: DatasetVersion['variables']
  aggregationCandidates: DatasetVersion['variables']
  controlCandidates: DatasetVersion['variables']
  longitudinalCandidates: Array<{ id: string; label: string }>
  longitudinalItemGroups: Array<{
    id: string
    label: string
    itemIds: string[]
    itemLabels: string[]
  }>
  subjectCandidates: DatasetVersion['variables']
  boundClusterId: string | null
  nestedContext: boolean
  initialOutcome: string | null
}

export function deriveEmpiricalState(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  analysisContext: ResolvedAnalysisContext | null | undefined,
): EmpiricalDerivedState {
  const scores = (measurement?.derivedDataset.scoreVariables ?? [])
  const itemIds = new Set((measurement?.constructs ?? []).flatMap((construct) => construct.itemIds))
  const groupCandidates = dataset.variables.filter(
    (variable) =>
      !itemIds.has(variable.id) &&
      ['binary', 'nominal', 'ordinal'].includes(variable.confirmedType ?? ''),
  )
  const boundClusterId = analysisContext?.structure?.roles?.clusterId ?? null
  const nestedContext = analysisContext?.studyContext?.value.dependenceStructure === 'nested'
  const aggregationCandidates = dataset.variables.filter(
    (variable) =>
      variable.id === boundClusterId ||
      (!itemIds.has(variable.id) &&
        ['id', 'binary', 'nominal', 'ordinal'].includes(
          variable.confirmedType ?? variable.inferredType,
        )),
  )
  const controlCandidates = dataset.variables.filter(
    (variable) =>
      !itemIds.has(variable.id) &&
      ['continuous', 'binary', 'ordinal'].includes(variable.confirmedType ?? ''),
  )
  const longitudinalCandidates = [
    ...scores,
    ...dataset.variables
      .filter(
        (variable) =>
          (analysisContext?.structure?.roles?.dataLayout === 'wide' ||
            !itemIds.has(variable.id)) &&
          ['continuous', 'binary', 'ordinal', 'likert'].includes(
            variable.confirmedType ?? '',
          ),
      )
      .map((variable) => ({ id: variable.id, label: variable.label })),
  ]
  const labels = new Map(dataset.variables.map((variable) => [variable.id, variable.label]))
  const longitudinalItemGroups = (measurement?.constructs ?? []).map((construct) => ({
    id: construct.id,
    label: construct.name,
    itemIds: construct.itemIds,
    itemLabels: construct.itemIds.map((itemId) => labels.get(itemId) ?? itemId),
  }))
  const boundSubjectId = analysisContext?.structure?.roles?.subjectId
  const subjectCandidates = dataset.variables.filter(
    (variable) =>
      variable.id === boundSubjectId || (variable.confirmedType ?? variable.inferredType) === 'id',
  )
  return {
    scores,
    groupCandidates,
    aggregationCandidates,
    controlCandidates,
    longitudinalCandidates,
    longitudinalItemGroups,
    subjectCandidates,
    boundClusterId,
    nestedContext,
    initialOutcome: scores.at(-1)?.id ?? null,
  }
}

export function initialEmpiricalConfig(
  measurement: MeasurementVersion | null,
  derived: EmpiricalDerivedState,
  researchParadigm: string,
): EmpiricalConfigValue {
  return {
    procedure: researchParadigm === 'longitudinal' ? 'longitudinal' : researchParadigm === 'diary' ? 'diary' : 'descriptives',
    analysisVariableIds: [],
    constructIds: [],
    factorCount: Math.max(1, (measurement?.constructs.length ?? 0)),
    groupVariableId: null,
    aggregationVariableId: derived.nestedContext ? derived.boundClusterId : null,
    outcomeVariableId: null,
    predictorVariableIds: [],
    controlVariableIds: [],
    responseSurfacePredictorIds: [],
    correlationMethod: 'pearson',
    correlationPAdjust: 'BH',
    groupOmnibusPAdjust: 'holm',
    multiplicityPAdjust: 'BH',
    confidenceLevel: 0.95,
    multiplicityFamilyId: 'cross_sectional_inference',
    rotation: 'varimax',
    factorCountMethod: 'kaiser',
    parallelIterations: 1000,
    randomSeed: 20260714,
    sampleVersionId: null,
    longitudinalPanel: null,
    diaryMultilevel: null,
  }
}

export function optionsFromEmpiricalConfig(
  config: EmpiricalConfigValue,
  analysisContext: ResolvedAnalysisContext | null | undefined,
): EmpiricalAnalysisOptions {
  const options: EmpiricalAnalysisOptions = {
    factorCount: config.factorCount,
    groupVariableId: config.groupVariableId,
    aggregationVariableId: config.aggregationVariableId,
    outcomeVariableId: config.outcomeVariableId,
    predictorVariableIds: config.predictorVariableIds,
    controlVariableIds: config.controlVariableIds,
    responseSurfacePredictorIds: config.responseSurfacePredictorIds,
    correlationMethod: config.correlationMethod,
    correlationPAdjust: config.correlationPAdjust,
    groupOmnibusPAdjust: config.groupOmnibusPAdjust,
    multiplicityPAdjust: config.multiplicityPAdjust,
    confidenceLevel: config.confidenceLevel,
    multiplicityFamilyId: config.multiplicityFamilyId,
    rotation: config.rotation,
    factorCountMethod: config.factorCountMethod,
    parallelIterations: config.parallelIterations,
    randomSeed: config.randomSeed,
    longitudinalPanel: config.longitudinalPanel,
    diaryMultilevel: config.diaryMultilevel,
  }
  options.procedure = config.procedure
  options.analysisVariableIds = ['descriptives', 'frequencies', 'missing', 'correlation', 'groups'].includes(config.procedure) ? config.analysisVariableIds : []
  options.constructIds = ['reliability', 'efa', 'cfa', 'validity', 'common_method', 'invariance', 'aggregation'].includes(config.procedure) ? config.constructIds : []
  if (!['groups', 'invariance'].includes(config.procedure)) options.groupVariableId = null
  if (config.procedure !== 'aggregation') options.aggregationVariableId = null
  if (!['regression', 'relative_importance', 'response_surface'].includes(config.procedure)) options.outcomeVariableId = null
  if (!['regression', 'relative_importance'].includes(config.procedure)) options.predictorVariableIds = []
  if (config.procedure !== 'response_surface') options.responseSurfacePredictorIds = []
  if (!['regression', 'relative_importance', 'response_surface'].includes(config.procedure) && !(config.procedure === 'correlation' && config.correlationMethod === 'partial')) options.controlVariableIds = []
  if (config.procedure !== 'longitudinal') options.longitudinalPanel = null
  if (config.procedure !== 'diary') options.diaryMultilevel = null
  if (analysisContext?.contextHash) options.contextHash = analysisContext.contextHash
  if (config.sampleVersionId) options.sampleVersionId = config.sampleVersionId
  return options
}
