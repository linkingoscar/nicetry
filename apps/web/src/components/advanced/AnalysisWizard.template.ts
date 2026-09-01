import type { DatasetVariableItem } from './DatasetVariablePicker'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import { adaptDraftRoles } from './draftAdapters'
import { buildPowerAnalysisSpec, buildExperimentalDesignSpec } from './AnalysisWizardSpecBuilders'
import {
  buildMultipleImputationSpec,
  buildMultilevelModelSpec,
  buildQuestionnaireMeasurementSpec,
} from './AnalysisWizardSpecBuildersRest'
import type { AnalysisSpecBuilderContext } from './AnalysisWizard.templateTypes'

export function buildAnalysisSpecTemplate(
  family: string,
  sliceId: string | undefined,
  datasetId: string | undefined,
  variables: DatasetVariableItem[],
  measurementConstructs: Array<{ id: string; label: string; itemIds: string[] }>,
  context?: ResolvedAnalysisContext | null,
): object {
  const numericIds = variables.filter(variable => variable.type === 'numeric').map(variable => variable.id)
  const categoricalIds = variables.filter(variable => variable.type === 'categorical').map(variable => variable.id)
  const itemIds = Array.from(new Set(
    measurementConstructs.flatMap(construct => construct.itemIds),
  )).filter(itemId => variables.some(variable => variable.id === itemId))
  const selectedItemIds = itemIds.length >= 2 ? itemIds : numericIds.slice(0, 8)
  const constructs = measurementConstructs
    .map(construct => ({
      id: construct.id,
      label: construct.label,
      itemIds: construct.itemIds.filter(itemId => selectedItemIds.includes(itemId)),
    }))
    .filter(construct => construct.itemIds.length >= 2)
  const fallbackMidpoint = Math.max(2, Math.ceil(selectedItemIds.length / 2))
  const selectedConstructs = constructs.length > 0 ? constructs : [
    { id: 'construct_a', label: '构念 A', itemIds: selectedItemIds.slice(0, fallbackMidpoint) },
    { id: 'construct_b', label: '构念 B', itemIds: selectedItemIds.slice(fallbackMidpoint) },
  ].filter(construct => construct.itemIds.length >= 2)
  const base: Record<string, unknown> = {
    schemaVersion: '0.1.0',
    analysisId: `analysis-${Date.now().toString(36)}`,
    name: '新分析',
    confidenceLevel: 0.95,
    seed: 20260714,
    ...(context ? {
      datasetVersionId: context.dataset.id,
      contextHash: context.contextHash,
      datasetSha256: context.dataset.sha256,
      sampleVersionId: context.sample.id,
      sampleHash: context.sample.hash,
      structureVersionId: context.structure?.id ?? null,
      structureHash: context.structure?.hash ?? null,
      measurementVersionId: context.measurement?.id ?? null,
      measurementHash: context.measurement?.hash ?? null,
    } : {}),
  }
  const applyContextRoles = (spec: Record<string, unknown>): Record<string, unknown> => {
    if (!context) return spec
    const defaults = adaptDraftRoles(sliceId ?? `${family}.default`, context)
    const next = { ...spec }
    if (family === 'multilevel_model' || family === 'multiple_imputation') {
      if (defaults.clusterId) next.clusterVariableId = defaults.clusterId
    }
    if (family === 'experimental_design') {
      if (defaults.subjectId) next.subjectId = defaults.subjectId
      if (defaults.clusterId) next.clusterVariableId = defaults.clusterId
      const treatmentOrGroup = defaults.treatmentId ?? defaults.groupId
      if (treatmentOrGroup) next.betweenFactors = [{ variableId: treatmentOrGroup, coding: 'sum' }]
    }
    return next
  }
  const template = (spec: object): object => applyContextRoles(spec as Record<string, unknown>)

  const builderContext: AnalysisSpecBuilderContext = {
    base,
    sliceId,
    datasetId,
    variables,
    numericIds,
    categoricalIds,
    selectedItemIds,
    selectedConstructs,
    context,
    template,
  }

  switch (family) {
    case 'power_analysis':
      return buildPowerAnalysisSpec(builderContext)
    case 'experimental_design':
      return buildExperimentalDesignSpec(builderContext)
    case 'multiple_imputation':
      return buildMultipleImputationSpec(builderContext)
    case 'multilevel_model':
      return buildMultilevelModelSpec(builderContext)
    case 'questionnaire_measurement':
      return buildQuestionnaireMeasurementSpec(builderContext)
    default:
      return template({ ...base, family })
  }
}
