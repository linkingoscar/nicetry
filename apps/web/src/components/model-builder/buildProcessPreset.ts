import type { MeasurementVersion, ModelSpec, ModelVariable } from '../../types'
import { processPresets } from './processPresets.generated'
import { processPresetGraph, presetDescription } from './processPresetGraph'
import { createEmptyNode, nodeFromVariable } from './modelTemplateNodes'
import { selectTemplateVariables, type StructuralRole } from './modelTemplateSelection'
import { templateLabels, type ModelTemplate } from './modelTemplateTypes'

export function buildProcessPreset(template: ModelTemplate, variables: ModelVariable[], measurement: MeasurementVersion, mediatorCount?: number): ModelSpec {
  const preset = processPresets.find(item => `model_${item.number}` === template)
  if (!preset) throw new Error('不支持的 PROCESS 预设编号')
  const graph = processPresetGraph(preset, mediatorCount)
  let selected: ModelVariable[] = []
  try { selected = selectTemplateVariables(template, variables, graph.nodes.map(n => n.role as StructuralRole)) } catch { /* Keep explicit empty slots when there are insufficient compatible variables. */ }
  const nodes = graph.nodes.map(({ symbol, role }, i) => ({ ...(selected[i] ? nodeFromVariable(role, selected[i]) : createEmptyNode(role)), id: `node_${symbol}` }))
  return {
    schemaVersion: '1.0.0', modelId: `model_${measurement.datasetVersionId.slice(-8)}`,
    name: templateLabels[template], description: presetDescription(preset), datasetVersionId: measurement.derivedDataset.id,
    design: { timeStructure: 'cross_sectional', clustering: 'none', claimMode: 'associational' },
    nodes, edges: graph.edges, moderations: graph.moderations, covariates: [],
    estimation: { family: 'ols', standardErrors: 'hc3', confidenceLevel: 0.95,
      bootstrap: { enabled: true, replicates: 5000, method: 'percentile', seed: 20260713 },
      missing: 'complete_cases_per_model', centering: { method: 'none', nodeIds: [] }, reportScale: 'unstandardized_primary' },
    canvas: { positions: graph.positions },
  }
}
