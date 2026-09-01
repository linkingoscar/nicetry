import type { MeasurementVersion, ModelEdge, ModelSpec, ModelVariable } from '../../types'
import { createEmptyNode, nodeFromVariable } from './modelTemplateNodes'
import { selectTemplateVariables, type StructuralRole } from './modelTemplateSelection'
import { templateLabels, type ModelTemplate } from './modelTemplateTypes'

export function buildModeratedMediationTemplate(
  template: Extract<ModelTemplate, 'model_8' | 'model_15' | 'model_21' | 'model_22' | 'model_58' | 'model_59'>,
  variables: ModelVariable[],
  measurement: MeasurementVersion,
): ModelSpec {
  const needsSecondModerator = template === 'model_21' || template === 'model_22'
  const roles: StructuralRole[] = ['x', 'm', 'y', 'w', ...(needsSecondModerator ? ['z' as const] : [])]
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
  const edges: ModelEdge[] = [
    { id: 'edge_x_m', from: 'node_x', to: 'node_m', kind: 'regression', label: 'a' },
    { id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression', label: 'c_prime' },
    { id: 'edge_m_y', from: 'node_m', to: 'node_y', kind: 'regression', label: 'b' },
  ]
  const moderationByTemplate: Record<'model_8' | 'model_15' | 'model_21' | 'model_22' | 'model_58' | 'model_59', ModelSpec['moderations']> = {
    model_8: [
        { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_m' },
        { id: 'moderation_w2', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_y', productTermId: 'term_interaction_y' },
    ],
    model_15: [
        { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_m_y', productTermId: 'term_interaction_m_y' },
        { id: 'moderation_w2', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_y', productTermId: 'term_interaction_x_y' },
    ],
    model_21: [
      { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_x_m' },
      { id: 'moderation_z1', moderatorNodeId: 'node_z', targetEdgeId: 'edge_m_y', productTermId: 'term_interaction_m_y' },
    ],
    model_22: [
      { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_x_m' },
      { id: 'moderation_z1', moderatorNodeId: 'node_z', targetEdgeId: 'edge_m_y', productTermId: 'term_interaction_m_y' },
      { id: 'moderation_w2', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_y', productTermId: 'term_interaction_x_y' },
    ],
    model_58: [
      { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_x_m' },
      { id: 'moderation_w2', moderatorNodeId: 'node_w', targetEdgeId: 'edge_m_y', productTermId: 'term_interaction_m_y' },
    ],
    model_59: [
      { id: 'moderation_w1', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_m', productTermId: 'term_interaction_x_m' },
      { id: 'moderation_w2', moderatorNodeId: 'node_w', targetEdgeId: 'edge_m_y', productTermId: 'term_interaction_m_y' },
      { id: 'moderation_w3', moderatorNodeId: 'node_w', targetEdgeId: 'edge_x_y', productTermId: 'term_interaction_x_y' },
    ],
  }
  const moderations = moderationByTemplate[template]
  const centerNodes = template === 'model_8'
    ? ['node_x', 'node_w']
    : needsSecondModerator
      ? ['node_x', 'node_m', 'node_w', 'node_z']
      : ['node_x', 'node_m', 'node_w']

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
    moderations,
    covariates: [],
    estimation: {
      family: 'ols',
      standardErrors: 'hc3',
      confidenceLevel: 0.95,
      bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 20260713 },
      missing: 'complete_cases_per_model',
      centering: {
        method: 'mean',
        nodeIds: centerNodes,
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
