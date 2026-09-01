import { describe, expect, it } from 'vitest'
import { processPresets } from './processPresets.generated'
import { processPresetGraph } from './processPresetGraph'

describe('PROCESS topology controls', () => {
  it('Model 91 moderates inter-mediator paths using W, not M1', () => {
    const preset = processPresets.find(p => p.number === 91)
    if (!preset) throw new Error('Missing 91')
    const graph = processPresetGraph(preset, 3)
    expect(graph.moderations.map(m => m.targetEdgeId)).toEqual(['edge_m1_m2', 'edge_m1_m3', 'edge_m2_m3'])
    expect(graph.moderations.every(m => m.moderatorNodeId === 'node_w')).toBe(true)
  })
  it('Model 82 keeps exactly two two-mediator chains and enforces its count', () => {
    const preset = processPresets.find(p => p.number === 82)
    if (!preset) throw new Error('Missing 82')
    expect(() => processPresetGraph(preset, 3)).toThrow('需要')
    const graph = processPresetGraph(preset, 4)
    expect(graph.edges.filter(e => e.from.startsWith('node_m') && e.to.startsWith('node_m')).map(e => e.id)).toEqual(['edge_m1_m2', 'edge_m3_m4'])
  })
})
