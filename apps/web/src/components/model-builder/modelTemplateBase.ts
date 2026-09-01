import type { MeasurementVersion, ModelEdge, ModelSpec, ModelVariable } from '../../types'
import { createEmptyNode, nodeFromVariable } from './modelTemplateNodes'
import { selectTemplateVariables, templateRoles } from './modelTemplateSelection'
import { templateLabels, type ModelTemplate } from './modelTemplateTypes'

export function buildBaseModelTemplate(
  template: Exclude<ModelTemplate, 'model_6' | 'model_8' | 'model_15' | 'model_21' | 'model_22' | 'model_58' | 'model_59'>,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  const roles = templateRoles(template)
  let selectedVars: ModelVariable[] = []
  try {
    if (variables && variables.length >= roles.length) {
      selectedVars = selectTemplateVariables(template, variables, roles)
    }
  } catch {
    // fallback
  }
  const nodes = roles.map((role, idx) => (
    selectedVars[idx] ? nodeFromVariable(role, selectedVars[idx]) : createEmptyNode(role)
  ))
  const edges: ModelEdge[] = template === 'model_1'
    || template === 'model_2'
    || template === 'model_3'
    ? [{ id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression', label: 'c' }]
    : [
        { id: 'edge_x_m', from: 'node_x', to: 'node_m', kind: 'regression', label: 'a' },
        { id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression', label: 'c_prime' },
        { id: 'edge_m_y', from: 'node_m', to: 'node_y', kind: 'regression', label: 'b' },
      ]
  const moderationTarget = template === 'model_1'
    ? 'edge_x_y'
    : template === 'model_5'
      ? 'edge_x_y'
    : template === 'model_7'
      ? 'edge_x_m'
      : template === 'model_14'
        ? 'edge_m_y'
        : null
  const centerSource = template === 'model_14' ? 'node_m' : 'node_x'
  const multiModeratorModerations: ModelSpec['moderations'] = template === 'model_2'
    || template === 'model_3'
    ? [
        {
          id: 'moderation_w',
          moderatorNodeId: 'node_w',
          targetEdgeId: 'edge_x_y',
          productTermId: 'term_x_w',
        },
        {
          id: 'moderation_z',
          moderatorNodeId: 'node_z',
          targetEdgeId: 'edge_x_y',
          productTermId: 'term_x_z',
        },
        ...(template === 'model_3'
          ? [{
              id: 'moderation_w_z',
              moderatorNodeId: 'node_w',
              secondaryModeratorNodeId: 'node_z',
              targetEdgeId: 'edge_x_y',
              productTermId: 'term_x_w_z',
              moderatorProductTermId: 'term_w_z',
            }]
          : []),
      ]
    : []
  return {
    schemaVersion: '1.0.0',
    modelId: `model_${measurement.datasetVersionId.slice(-8)}`,
    name: templateLabels[template],
    description: '由 M3 模型画布创建。',
    datasetVersionId: measurement.derivedDataset.id,
    design: {
      timeStructure: 'cross_sectional',
      clustering: 'none',
      claimMode: 'associational',
    },
    nodes,
    edges,
    moderations: multiModeratorModerations.length > 0
      ? multiModeratorModerations
      : moderationTarget
      ? [{
          id: 'moderation_w',
          moderatorNodeId: 'node_w',
          targetEdgeId: moderationTarget,
          productTermId: 'term_interaction',
        }]
      : [],
    covariates: [],
    estimation: {
      family: 'ols',
      standardErrors: 'hc3',
      confidenceLevel: 0.95,
      bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 20260713 },
      missing: 'complete_cases_per_model',
      centering: {
        method: moderationTarget || multiModeratorModerations.length > 0 ? 'mean' : 'none',
        nodeIds: multiModeratorModerations.length > 0
          ? ['node_x', 'node_w', 'node_z']
          : moderationTarget ? [centerSource, 'node_w'] : [],
      },
      reportScale: 'unstandardized_primary',
    },
    canvas: {
      positions: {
        node_x: { x: 60, y: 150 },
        node_m: { x: 340, y: 70 },
        node_y: { x: 650, y: 150 },
        node_w: { x: 250, y: 300 },
        node_z: { x: 470, y: 300 },
      },
    },
  }
}
