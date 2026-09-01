import type { MeasurementVersion, ModelEdge, ModelSpec, ModelVariable } from '../../types'
import { createEmptyNode, nodeFromVariable } from './modelTemplateNodes'
import { selectTemplateVariables, type StructuralRole } from './modelTemplateSelection'
import { templateLabels } from './modelTemplateTypes'

export function buildModel6Template(
  measurement: MeasurementVersion,
  variables: ModelVariable[],
): ModelSpec {
  const roles: StructuralRole[] = ['x', 'm', 'm', 'y']
  let selectedVars: ModelVariable[] = []
  try {
    if (variables && variables.length >= roles.length) {
      selectedVars = selectTemplateVariables('model_6', variables, roles)
    }
  } catch {
    // fallback
  }
  const nodes = [
    selectedVars[0] ? nodeFromVariable('x', selectedVars[0]) : createEmptyNode('x'),
    selectedVars[1] ? nodeFromVariable('m', selectedVars[1], '1') : createEmptyNode('m', '1'),
    selectedVars[2] ? nodeFromVariable('m', selectedVars[2], '2') : createEmptyNode('m', '2'),
    selectedVars[3] ? nodeFromVariable('y', selectedVars[3]) : createEmptyNode('y'),
  ]
  const edges: ModelEdge[] = [
    { id: 'edge_x_m1', from: 'node_x', to: 'node_m1', kind: 'regression', label: 'a1' },
    { id: 'edge_x_m2', from: 'node_x', to: 'node_m2', kind: 'regression', label: 'a2' },
    { id: 'edge_m1_m2', from: 'node_m1', to: 'node_m2', kind: 'regression', label: 'd' },
    { id: 'edge_m1_y', from: 'node_m1', to: 'node_y', kind: 'regression', label: 'b1' },
    { id: 'edge_m2_y', from: 'node_m2', to: 'node_y', kind: 'regression', label: 'b2' },
    { id: 'edge_x_y', from: 'node_x', to: 'node_y', kind: 'regression', label: 'c_prime' },
  ]
  return {
    schemaVersion: '1.0.0',
    modelId: `model_${measurement.datasetVersionId.slice(-8)}`,
    name: templateLabels.model_6,
    description: '由 M3 模型画布创建。',
    datasetVersionId: measurement.derivedDataset.id,
    design: {
      timeStructure: 'cross_sectional',
      clustering: 'none',
      claimMode: 'associational',
    },
    nodes,
    edges,
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
        node_m1: { x: 260, y: 50 },
        node_m2: { x: 460, y: 50 },
        node_y: { x: 650, y: 150 },
      },
    },
  }
}
