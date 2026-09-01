import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect, test } from '@playwright/test'
import { processPresets } from '../../apps/web/src/components/model-builder/processPresets.generated'
import { processPresetGraph } from '../../apps/web/src/components/model-builder/processPresetGraph'
import { templateLabels } from '../../apps/web/src/components/model-builder/modelTemplateTypes'

test.describe('official PROCESS preset contract', () => {
  test('round trips all 55 front-end presets and mediator boundaries through Python recognition', () => {
    const models = processPresets.flatMap(preset => [...new Set([preset.minM, preset.maxM])].map(count => {
      const graph = processPresetGraph(preset, count)
      return { expected: preset.number, model: {
        schemaVersion: '1.0.0', modelId: 'model_roundtrip', name: templateLabels[`model_${preset.number}`], datasetVersionId: 'derived_roundtrip',
        design: { timeStructure: 'cross_sectional', clustering: 'none', claimMode: 'associational' },
        nodes: graph.nodes.map(n => ({ id: `node_${n.symbol}`, role: n.role, variableId: `var_${n.symbol}`, label: n.symbol, kind: 'observed', dataType: 'continuous' })),
        edges: graph.edges, moderations: graph.moderations, covariates: [], canvas: { positions: graph.positions },
        estimation: { family: 'ols', standardErrors: 'hc3', confidenceLevel: 0.95, bootstrap: { enabled: true, replicates: 1000, method: 'percentile', seed: 100 }, missing: 'complete_cases_per_model', centering: { method: 'none', nodeIds: [] }, reportScale: 'unstandardized_primary' },
      } }
    }))
    const root = resolve(process.cwd())
    const python = resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python')
    const script = `import json, sys
from pathlib import Path
sys.path.insert(0, 'apps/api')
from app.contracts import validate_contract
from app.semantics import validate_model_semantics
items=json.load(sys.stdin)
for item in items:
    validate_contract(item['model'], Path('specs/model-spec.schema.json'))
    result=validate_model_semantics(item['model'])
    assert result['valid'], (item['expected'], result)
    assert result['processModelNumber']==item['expected'], (item['expected'], result)
    assert result['executionAvailable'], (item['expected'], result)
print(len(items))`
    const result = execFileSync(python, ['-c', script], { cwd: root, input: JSON.stringify(models), encoding: 'utf8', timeout: 60000 })
    expect(Number(result.trim())).toBe(models.length)
    expect(processPresets).toHaveLength(55)
    expect(Object.keys(templateLabels)).toHaveLength(55)
    expect(Object.keys(templateLabels)).not.toContain('model_74')
  })

  test('never silently adjusts out-of-range mediator counts', () => {
    const preset = processPresets.find(p => p.number === 82)
    if (!preset) throw new Error('Missing Model 82')
    expect(() => processPresetGraph(preset, 3)).toThrow('需要')
    expect(() => processPresetGraph(preset, 5)).toThrow('需要')
  })
})
