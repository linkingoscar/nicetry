import type { Connection } from '@xyflow/react'
import type { ModelSpec, ModelVariable, NodeRole } from '../../types'
import { nodeFromVariable } from './modelTemplates'
import { addVariableToCanvasModel, changeModelNodeRole, reconnectModelEdge } from './modelCanvasActions'
import { removeStructuralNodeModel } from './modelStructureActions'

export function createModelCanvasHandlers(
  variables: ModelVariable[],
  model: ModelSpec,
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void,
  assignVariable: (nodeId: string, variableId: string) => void,
  setBuilderError: (msg: string | null) => void,
) {
  const addCovariate = (variableId: string) => {
    const variable = variables.find((item) => item.id === variableId)
    if (!variable || model.nodes.some((node) => node.variableId === variableId)) return
    updateModel((current) => {
      const nodeId = `node_cov_${variable.id.replace(/[^A-Za-z0-9_-]/g, '_')}`
      const outcome = current.nodes.find((node) => node.role === 'y')
      return {
        ...current,
        nodes: [...current.nodes, { ...nodeFromVariable('covariate', variable), id: nodeId }],
        covariates: outcome
          ? [...current.covariates, { nodeId, outcomeNodeIds: [outcome.id] }]
          : current.covariates,
        canvas: {
          positions: {
            ...current.canvas?.positions,
            [nodeId]: { x: 470, y: 310 + current.covariates.length * 80 },
          },
        },
      }
    })
  }

  const addVariableToCanvas = (variableId: string, position: { x: number; y: number }, targetNodeId?: string, role?: NodeRole) => {
    const variable = variables.find((item) => item.id === variableId)
    if (!variable) return
    if (targetNodeId) {
      assignVariable(targetNodeId, variableId)
      return
    }
    if (model.nodes.some((node) => node.variableId === variableId)) {
      setBuilderError(`变量“${variable.label}”已经绑定到画布节点；可直接拖到目标节点替换。`)
      return
    }

    if (!role) { setBuilderError('请先选择新节点的变量角色。'); return }
    try {
      const next = addVariableToCanvasModel(model, variable, position, role)
      setBuilderError(null)
      updateModel(() => next)
    } catch (error) { setBuilderError(error instanceof Error ? error.message : '变量放置失败') }
  }

  const addEdge = (source: string, target: string) => {
    if (!source || !target || source === target) return
    updateModel((current) => {
      if (current.edges.some((edge) => edge.from === source && edge.to === target)) return current
      const id = `edge_${source.replace('node_', '')}_${target.replace('node_', '')}`
      return {
        ...current,
        edges: [...current.edges, { id, from: source, to: target, kind: 'regression', label: '' }],
      }
    })
  }

  const removeCanvasNode = (nodeId: string) => {
    updateModel((current) => removeStructuralNodeModel(current, nodeId))
  }

  const changeNodeRole = (nodeId: string, newRole: NodeRole) => {
    const next = changeModelNodeRole(model, nodeId, newRole)
    if (next === model) return
    if (!window.confirm('修改角色时，如 X / Y / W / Z 已存在，将交换两者角色；不再适用的路径、调节或控制关系会清除。变量绑定保留，可撤销恢复。是否继续？')) return
    updateModel(() => next)
  }

  const reconnectEdge = (id: string, from: string, to: string) => {
    try { const next = reconnectModelEdge(model, id, from, to); setBuilderError(null); updateModel(() => next) }
    catch (error) { setBuilderError(error instanceof Error ? error.message : '路径修改失败') }
  }

  const handleConnect = (connection: Connection) => {
    if (!connection.source || !connection.target || connection.source === connection.target) return

    const sourceNode = model.nodes.find((n) => n.id === connection.source)
    if (!sourceNode) return

    if (sourceNode.role === 'covariate') {
      const target = model.nodes.find(n => n.id === connection.target)
      if (!target || !['m', 'y'].includes(target.role)) { setBuilderError('控制变量只能进入 M 或 Y 方程。'); return }
      updateModel(current => {
        const existing = current.covariates.find(c => c.nodeId === sourceNode.id)
        return { ...current, covariates: [...current.covariates.filter(c => c.nodeId !== sourceNode.id), { nodeId: sourceNode.id, outcomeNodeIds: [...new Set([...(existing?.outcomeNodeIds ?? []), target.id])] }] }
      })
      return
    }

    if (sourceNode.role === 'w' || sourceNode.role === 'z') {
      const targetEdges = model.edges.filter((e) => e.to === connection.target && e.from !== connection.source)
      if (targetEdges.length !== 1) {
        setBuilderError('无法唯一确定被调节的路径。请打开“路径与调节”，在具体路径旁选择 W 或 Z。')
        return
      }
      if (targetEdges.length > 0) {
        const targetEdge = targetEdges.find((e) => e.from !== connection.source) ?? targetEdges[0]
        if (targetEdge) {
          updateModel((current) => {
            if (current.moderations.some((m) => m.moderatorNodeId === connection.source && m.targetEdgeId === targetEdge.id)) {
              return current
            }
            const modId = `moderation_${sourceNode.role}_${targetEdge.id}`
            const termId = `term_interaction_${sourceNode.role}_${targetEdge.id}`
            return {
              ...current,
              moderations: [
                ...current.moderations,
                {
                  id: modId,
                  moderatorNodeId: sourceNode.id,
                  targetEdgeId: targetEdge.id,
                  productTermId: termId,
                },
              ],
            }
          })
          return
        }
      }
    }

    addEdge(connection.source, connection.target)
  }

  return {
    addCovariate,
    addVariableToCanvas,
    addEdge,
    removeCanvasNode,
    changeNodeRole,
    handleConnect,
    reconnectEdge,
  }
}
