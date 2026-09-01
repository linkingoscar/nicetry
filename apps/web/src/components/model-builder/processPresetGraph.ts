import type { ModelEdge, ModelModeration, NodeRole } from '../../types'
import type { processPresets } from './processPresets.generated'

export type ProcessNumber = typeof processPresets[number]['number']
export type ProcessPreset = typeof processPresets[number]

export function presetGroup(preset: ProcessPreset): string {
  if (preset.number < 4) return '调节效应'
  if (preset.number >= 80 || preset.number === 6) return '链式与复合中介'
  if (!preset.bits.some(Boolean)) return '中介分析'
  return '有调节的中介'
}

export function presetDescription(preset: ProcessPreset): string {
  const targets = ['X→M', 'M→Y', 'X→Y']
  const details = targets.flatMap((target, index) => {
    const bits = preset.bits.slice(index * 3, index * 3 + 3)
    const modifiers = bits.flatMap((enabled, i) => enabled ? [['W', 'Z', 'W×Z'][i]] : [])
    return modifiers.length ? [`${target}：${modifiers.join('、')}`] : []
  })
  if (preset.firstOnly) details.push('W 仅调节首个中介的输入路径')
  if (preset.lastOnly) details.push('W 仅调节末个中介的输出路径')
  if (preset.serialModeration) details.push('W 调节中介间路径')
  return details.join('；') || (preset.number === 80 ? '前部并行中介汇入末个中介' : preset.number === 81 ? '首个中介分流至后部中介' : preset.number === 82 ? '两组双中介链' : preset.number === 6 ? '按顺序连接所有中介路径' : 'X→M→Y 与直接路径；可配置并行中介')
}

export function processPresetGraph(preset: ProcessPreset, count: number = preset.minM) {
  if (!Number.isInteger(count) || count < preset.minM || count > preset.maxM) throw new Error(`Model ${preset.number} 需要 ${preset.minM}–${preset.maxM} 个中介`)
  const mediators = Array.from({ length: count }, (_, i) => count === 1 ? 'm' : `m${i + 1}`)
  const pairs: Array<[string, string]> = [['x', 'y'], ...mediators.map(m => ['x', m] as [string, string]), ...mediators.map(m => [m, 'y'] as [string, string])]
  const serial = preset.number === 6 || preset.number >= 83
  if (serial) for (let to = 1; to < count; to++) for (let from = 0; from < to; from++) pairs.push([mediators[from], mediators[to]])
  if (preset.number === 80) for (const m of mediators.slice(0, -1)) pairs.push([m, mediators[count - 1]])
  if (preset.number === 81) for (const m of mediators.slice(1)) pairs.push([mediators[0], m])
  if (preset.number === 82) pairs.push([mediators[0], mediators[1]], [mediators[2], mediators[3]])
  const edges: ModelEdge[] = pairs.map(([from, to]) => ({ id: `edge_${from}_${to}`, from: `node_${from}`, to: `node_${to}`, kind: 'regression', label: `${from.toUpperCase()}→${to.toUpperCase()}` }))
  const moderations: ModelModeration[] = []
  const add = (edge: ModelEdge, w: 'w' | 'z' | 'wz') => {
    const id = `${w}_${edge.id}`
    moderations.push({ id: `moderation_${id}`, targetEdgeId: edge.id, moderatorNodeId: w === 'z' ? 'node_z' : 'node_w', productTermId: `term_${id}`,
      ...(w === 'wz' ? { secondaryModeratorNodeId: 'node_z', moderatorProductTermId: 'term_w_z' } : {}) })
  }
  edges.forEach(edge => {
    const from = edge.from.slice(5), to = edge.to.slice(5)
    const group = from === 'x' && mediators.includes(to) ? 0 : mediators.includes(from) && to === 'y' ? 1 : from === 'x' && to === 'y' ? 2 : -1
    if (group >= 0) for (let i = 0; i < 3; i++) {
      if (!preset.bits[group * 3 + i]) continue
      if (i === 0 && group === 0 && preset.firstOnly && to !== mediators[0]) continue
      if (i === 0 && group === 1 && preset.lastOnly && from !== mediators[count - 1]) continue
      add(edge, (['w', 'z', 'wz'] as const)[i])
    }
    if (preset.serialModeration && mediators.includes(from) && mediators.includes(to)) add(edge, 'w')
  })
  const symbols = ['x', ...mediators, 'y']
  if (moderations.some(m => m.moderatorNodeId === 'node_w')) symbols.push('w')
  if (moderations.some(m => m.moderatorNodeId === 'node_z' || m.secondaryModeratorNodeId === 'node_z')) symbols.push('z')
  const nodes = symbols.map(symbol => ({ symbol, role: (symbol.startsWith('m') ? 'm' : symbol) as NodeRole }))
  const positions: Record<string, { x: number; y: number }> = { node_x: { x: 40, y: 210 }, node_y: { x: serial ? 370 + count * 220 : 700, y: 210 }, node_w: { x: 170, y: 0 }, node_z: { x: 510, y: 0 } }
  mediators.forEach((m, i) => { positions[`node_${m}`] = { x: serial ? 270 + i * 220 : 360, y: serial ? 150 + i * 90 : 130 + i * 150 } })
  return { nodes, edges, moderations, positions }
}
