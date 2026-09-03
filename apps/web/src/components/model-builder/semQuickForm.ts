import type { MeasurementVersion, ModelSpec, ModelVariable } from '../../types'
import { buildModelForEstimationFamily } from './modelBuilderEstimation'
import { assignVariableToModel } from './modelStructureActions'
import { createCustomModelTemplate } from './modelTemplates'

export interface SemQuickSetup {
  predictorVariableId: string
  outcomeVariableId: string
  estimator: 'ML' | 'WLSMV'
  confidenceLevel: number
  missing: 'fiml' | 'complete_cases_per_model'
}

export function buildBasicSemModel(
  setup: SemQuickSetup,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  if (!setup.predictorVariableId || !setup.outcomeVariableId) throw new Error('请选择预测构念和结果构念。')
  if (setup.predictorVariableId === setup.outcomeVariableId) throw new Error('预测构念与结果构念必须不同。')
  if (!Number.isFinite(setup.confidenceLevel) || setup.confidenceLevel <= 0 || setup.confidenceLevel >= 1) {
    throw new Error('置信水平必须介于 0 和 1 之间。')
  }

  const predictorConstruct = measurement.constructs.find(
    (construct) => construct.outputVariableId === setup.predictorVariableId,
  )
  const outcomeConstruct = measurement.constructs.find(
    (construct) => construct.outputVariableId === setup.outcomeVariableId,
  )
  if (!predictorConstruct || !outcomeConstruct) throw new Error('所选构念已不在当前测量版本中。')

  const predictor = variables.find((variable) => variable.id === setup.predictorVariableId)
  const outcome = variables.find((variable) => variable.id === setup.outcomeVariableId)
  if (!predictor || !outcome) throw new Error('所选构念分数已不在当前派生数据中。')

  let model = createCustomModelTemplate(variables, measurement)
  model = assignVariableToModel(model, 'node_x', predictor, variables)
  model = assignVariableToModel(model, 'node_y', outcome, variables)
  model = {
    ...model,
    name: `基础 SEM · ${predictorConstruct.name} → ${outcomeConstruct.name}`,
    description: '由基础 SEM 表单创建；测量题项来自当前 MeasurementVersion。',
    edges: [{ id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression', label: 'β' }],
    moderations: [],
    covariates: [],
  }
  model = buildModelForEstimationFamily(model, 'sem', variables, measurement)

  return {
    ...model,
    estimation: {
      ...model.estimation,
      estimator: setup.estimator,
      confidenceLevel: setup.confidenceLevel,
      missing: setup.estimator === 'WLSMV' ? 'complete_cases_per_model' : setup.missing,
      groupVariableId: null,
      invariance: false,
      multiGroup: {
        compareStructuralPaths: false,
        estimateLatentMeans: false,
      },
    },
  }
}
