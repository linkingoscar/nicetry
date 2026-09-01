import type { ModelSpec, ModelVariable, VariableEncodingMethod } from '../../types'
import { removeStructuralNodeModel } from './modelStructureActions'

interface CovariateEditorProps {
  model: ModelSpec
  variables: ModelVariable[]
  unusedVariables: ModelVariable[]
  onAdd: (variableId: string) => void
  onChange: (model: ModelSpec) => void
}

const encodingLabels: Record<VariableEncodingMethod, string> = {
  as_is: '保持原值',
  mean_center: '均值中心化',
  standardize: 'Z 标准化',
  binary_indicator: '二元指示编码（0/1）',
  ordinal_score: '有序得分编码',
  treatment: '虚拟编码（k−1）',
}

function methodsFor(variable: ModelVariable): VariableEncodingMethod[] {
  if (variable.dataType === 'nominal') return ['treatment']
  if (variable.dataType === 'binary') return ['binary_indicator']
  if (variable.dataType === 'ordinal') return ['ordinal_score', 'treatment', 'as_is']
  return ['as_is', 'mean_center', 'standardize']
}

export function CovariateEditor({ model, variables, unusedVariables, onAdd, onChange }: CovariateEditorProps) {
  const assignments = model.nodes.filter(node => node.role === 'covariate').map(node => model.covariates.find(item => item.nodeId === node.id) ?? { nodeId: node.id, outcomeNodeIds: [] })
  const updateNodeEncoding = (nodeId: string, method: VariableEncodingMethod, referenceLevel?: string) => {
    onChange({
      ...model,
      nodes: model.nodes.map((node) => node.id === nodeId
        ? { ...node, encoding: { ...node.encoding, method, referenceLevel: referenceLevel ?? node.encoding?.referenceLevel } }
        : node),
    })
  }

  const moveOrdinalLevel = (nodeId: string, levels: string[], index: number, direction: -1 | 1) => {
    const destination = index + direction
    if (destination < 0 || destination >= levels.length) return
    const reordered = [...levels]
    ;[reordered[index], reordered[destination]] = [reordered[destination], reordered[index]]
    onChange({
      ...model,
      nodes: model.nodes.map((node) => node.id === nodeId
        ? { ...node, encoding: { ...node.encoding, method: 'ordinal_score', levels: reordered } }
        : node),
    })
  }

  return (
    <section
      className="covariate-editor"
      aria-labelledby="covariate-heading"
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => onAdd(event.dataTransfer.getData('text/researchpath-variable'))}
    >
      <div className="section-heading dictionary-heading-row">
        <div><p className="eyebrow">Equation controls</p><h2 id="covariate-heading">控制变量与预编码</h2></div>
        <select aria-label="添加控制变量" defaultValue="" onChange={(event) => { onAdd(event.target.value); event.target.value = '' }}>
          <option value="">添加控制变量…</option>
          {unusedVariables.map((variable) => <option key={variable.id} value={variable.id}>{variable.label} · {variable.encodingHint.label}</option>)}
        </select>
      </div>
      <p className="muted">系统按字典类型预设编码；添加后请确认参照组、顺序和进入的方程。量表题优先使用上方已经过计分规则处理的构念得分。</p>
      {assignments.length === 0 ? <div className="covariate-empty">从上方菜单添加，或将左侧变量分配为控制变量；也支持拖入。</div> : null}
      <div className="covariate-list">
        {assignments.map((assignment) => {
          const node = model.nodes.find((item) => item.id === assignment.nodeId)
          const variable = variables.find((item) => item.id === node?.variableId)
          if (!node || !variable) return null
          const levels = node.encoding?.levels ?? variable.encodingHint.levels ?? []
          const outcomes = model.nodes.filter((item) => item.role === 'm' || item.role === 'y')
          return (
            <article className="covariate-card" key={assignment.nodeId}>
              <div className="covariate-title">
                <div><strong>{node.label}</strong><small>{variable.source} · {variable.dataType}</small></div>
                <span className="encoding-badge">{encodingLabels[node.encoding?.method ?? variable.encodingHint.method]}</span>
              </div>
              <label>预编码方式
                <select value={node.encoding?.method ?? variable.encodingHint.method} onChange={(event) => updateNodeEncoding(node.id, event.target.value as VariableEncodingMethod)}>
                  {methodsFor(variable).map((method) => <option value={method} key={method}>{encodingLabels[method]}</option>)}
                </select>
              </label>
              {(node.encoding?.method === 'treatment' || node.encoding?.method === 'binary_indicator') && levels.length ? (
                <label>参照组（系数相对该组）
                  <select value={node.encoding.referenceLevel ?? levels[0]} onChange={(event) => updateNodeEncoding(node.id, node.encoding?.method ?? 'treatment', event.target.value)}>
                    {levels.map((level) => <option key={level} value={level}>{level}</option>)}
                  </select>
                </label>
              ) : null}
              {node.encoding?.method === 'ordinal_score' && levels.length ? (
                <div className="ordinal-levels">
                  <span>低 → 高（可调整）</span>
                  {levels.map((level, index) => (
                    <span className="ordinal-level" key={level}>
                      <i>{index + 1}. {level}</i>
                      <button type="button" aria-label={`${level} 上移`} disabled={index === 0} onClick={() => moveOrdinalLevel(node.id, levels, index, -1)}>↑</button>
                      <button type="button" aria-label={`${level} 下移`} disabled={index === levels.length - 1} onClick={() => moveOrdinalLevel(node.id, levels, index, 1)}>↓</button>
                    </span>
                  ))}
                </div>
              ) : null}
              <fieldset className="covariate-outcomes">
                <legend>进入方程</legend>
                {outcomes.map((outcome) => (
                  <label key={outcome.id}>
                    <input
                      type="checkbox"
                      checked={assignment.outcomeNodeIds.includes(outcome.id)}
                      onChange={() => onChange({
                        ...model,
                        covariates: assignments.map((item) => item.nodeId === assignment.nodeId
                          ? { ...item, outcomeNodeIds: item.outcomeNodeIds.includes(outcome.id) ? item.outcomeNodeIds.filter((id) => id !== outcome.id) : [...item.outcomeNodeIds, outcome.id] }
                          : item),
                      })}
                    />
                    {outcome.role.toUpperCase()} 方程
                  </label>
                ))}
              </fieldset>
              <button type="button" className="text-button" aria-label={`移除控制变量 ${node.label}`}
                onClick={() => onChange(removeStructuralNodeModel(model, assignment.nodeId))}>移除</button>
            </article>
          )
        })}
      </div>
    </section>
  )
}
