import type { MeasurementVersion, ModelSpec, ModelVariable } from '../../types'
import { buildModel6Template } from './modelTemplateBuilder6'
import { buildBaseModelTemplate } from './modelTemplateBase'
import { buildModeratedMediationTemplate } from './modelTemplateModerated'
import { createEmptyNode } from './modelTemplateNodes'
import type { StructuralRole } from './modelTemplateSelection'
import type { ModelTemplate } from './modelTemplateTypes'
import { buildProcessPreset } from './buildProcessPreset'

const MODERATED_MEDIATION_TEMPLATES = [
  'model_8',
  'model_15',
  'model_21',
  'model_22',
  'model_58',
  'model_59',
] as const

export function createModelTemplate(
  template: ModelTemplate,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
  mediatorCount?: number,
): ModelSpec {
  if (mediatorCount !== undefined || !['model_1', 'model_2', 'model_3', 'model_4', 'model_5', 'model_6', 'model_7', 'model_8', 'model_14', 'model_15', 'model_21', 'model_22', 'model_58', 'model_59'].includes(template)) {
    return buildProcessPreset(template, variables, measurement, mediatorCount)
  }
  if (template === 'model_6') {
    return buildModel6Template(measurement, variables)
  }
  if ((MODERATED_MEDIATION_TEMPLATES as readonly string[]).includes(template)) {
    return buildModeratedMediationTemplate(
      template as (typeof MODERATED_MEDIATION_TEMPLATES)[number],
      variables,
      measurement,
    )
  }
  return buildBaseModelTemplate(
    template as Exclude<ModelTemplate, 'model_6' | 'model_8' | 'model_15' | 'model_21' | 'model_22' | 'model_58' | 'model_59'>,
    variables,
    measurement,
  )
}

export function createCustomModelTemplate(
  _variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  const roles: StructuralRole[] = ['x', 'y']
  const nodes = roles.map(role => createEmptyNode(role))
  return {
    schemaVersion: '1.0.0',
    modelId: `model_${measurement.datasetVersionId.slice(-8)}`,
    name: '自定义 PROCESS 结构',
    description: '从空白 X、Y 槽位开始；拖入变量后指定角色，再自行连接路径。',
    datasetVersionId: measurement.derivedDataset.id,
    design: {
      timeStructure: 'cross_sectional',
      clustering: 'none',
      claimMode: 'associational',
    },
    nodes,
    edges: [],
    moderations: [],
    covariates: [],
    estimation: {
      family: 'ols',
      standardErrors: 'hc3',
      confidenceLevel: 0.95,
      bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 20260713 },
      missing: 'complete_cases_per_model',
      centering: { method: 'none', nodeIds: [] },
      reportScale: 'unstandardized_primary',
    },
    canvas: {
      positions: {
        node_x: { x: 60, y: 150 },
        node_y: { x: 650, y: 150 },
      },
    },
  }
}
