import type { ModelEdge, ModelSpec } from '../../types'

interface ModerationEditorProps {
  model: ModelSpec
  onChange: (moderations: ModelSpec['moderations']) => void
}

interface ModerationPreset {
  id: string
  title: string
  detail: string
  edges: ModelEdge[]
}

function relationship(edge: ModelEdge, model: ModelSpec) {
  const source = model.nodes.find((node) => node.id === edge.from)?.role.toUpperCase()
  const target = model.nodes.find((node) => node.id === edge.to)?.role.toUpperCase()
  return `${source}→${target}`
}

function presetsFor(model: ModelSpec): ModerationPreset[] {
  const pair = (from: string, to: string) => model.edges.find((edge) => {
    const source = model.nodes.find((node) => node.id === edge.from)?.role
    const target = model.nodes.find((node) => node.id === edge.to)?.role
    return source === from && target === to
  })
  const direct = pair('x', 'y')
  const first = pair('x', 'm')
  const second = pair('m', 'y')
  const hasSecondModerator = model.nodes.some((node) => node.role === 'z')
  if (!first && !second && direct && hasSecondModerator) {
    return [
      { id: 'model_2', title: '两个独立调节', detail: 'Model 2 · W、Z 分别调节 X→Y', edges: [direct] },
      { id: 'model_3', title: '三阶交互', detail: 'Model 3 · 增加 W×Z 和 X×W×Z', edges: [direct] },
    ]
  }
  if (!first && !second && direct) {
    return [{ id: 'model_1', title: '调节主效应', detail: 'W 改变 X→Y 的斜率', edges: [direct] }]
  }
  if (first && second && direct && hasSecondModerator) {
    return [
      { id: 'model_21', title: '双调节的前、后半段', detail: 'Model 21 · W 调节 X→M，Z 调节 M→Y', edges: [first, second] },
      { id: 'model_22', title: '双调节的全部路径', detail: 'Model 22 · Model 21 加上 W 调节 X→Y', edges: [first, second, direct] },
    ]
  }
  return [
    direct ? { id: 'model_5', title: '仅直接效应', detail: 'Model 5 · 仅调节 X→Y（直接路径）', edges: [direct] } : null,
    first ? { id: 'model_7', title: '中介前半段', detail: 'Model 7 · 仅调节 X→M（a 路径）', edges: [first] } : null,
    second ? { id: 'model_14', title: '中介后半段', detail: 'Model 14 · 仅调节 M→Y（b 路径）', edges: [second] } : null,
    first && direct ? { id: 'model_8', title: '前半段 + 直接效应', detail: 'Model 8 · 同时调节 X→M 与 X→Y', edges: [first, direct] } : null,
    second && direct ? { id: 'model_15', title: '后半段 + 直接效应', detail: 'Model 15 · 同时调节 M→Y 与 X→Y', edges: [second, direct] } : null,
    first && second ? { id: 'model_58', title: '前、后半段', detail: 'Model 58 · 同时调节 X→M 与 M→Y', edges: [first, second] } : null,
    first && second && direct ? { id: 'model_59', title: '全部三条路径', detail: 'Model 59 · 同时调节 X→M、M→Y 与 X→Y', edges: [first, second, direct] } : null,
  ].filter((preset): preset is ModerationPreset => preset !== null)
}

function presetModerations(model: ModelSpec, preset: ModerationPreset): ModelSpec['moderations'] {
  const moderatorNodeId = model.nodes.find((node) => node.role === 'w')?.id ?? 'node_w'
  const secondaryModeratorNodeId = model.nodes.find((node) => node.role === 'z')?.id ?? 'node_z'
  if (preset.id === 'model_2' || preset.id === 'model_3') {
    const targetEdgeId = preset.edges[0].id
    return [
      {
        id: 'moderation_w',
        moderatorNodeId,
        targetEdgeId,
        productTermId: 'term_x_w',
      },
      {
        id: 'moderation_z',
        moderatorNodeId: secondaryModeratorNodeId,
        targetEdgeId,
        productTermId: 'term_x_z',
      },
      ...(preset.id === 'model_3'
        ? [{
            id: 'moderation_w_z',
            moderatorNodeId,
            secondaryModeratorNodeId,
            targetEdgeId,
            productTermId: 'term_x_w_z',
            moderatorProductTermId: 'term_w_z',
          }]
        : []),
    ]
  }
  if (preset.id === 'model_21' || preset.id === 'model_22') {
    const [first, second, direct] = preset.edges
    return [
      {
        id: 'moderation_x_m',
        moderatorNodeId,
        targetEdgeId: first.id,
        productTermId: 'term_interaction_x_m',
      },
      {
        id: 'moderation_m_y',
        moderatorNodeId: secondaryModeratorNodeId,
        targetEdgeId: second.id,
        productTermId: 'term_interaction_m_y',
      },
      ...(direct
        ? [{
            id: 'moderation_x_y',
            moderatorNodeId,
            targetEdgeId: direct.id,
            productTermId: 'term_interaction_x_y',
          }]
        : []),
    ]
  }
  return preset.edges.map((edge) => {
    const suffix = edge.id.replace(/^edge_/, '').replace(/[^A-Za-z0-9_-]/g, '_')
    return {
      id: `moderation_${suffix}`,
      moderatorNodeId,
      targetEdgeId: edge.id,
      productTermId: `term_interaction_${suffix}`,
    }
  })
}

function moderationSignature(moderations: ModelSpec['moderations']) {
  return moderations
    .map((item) => [
      item.targetEdgeId,
      item.moderatorNodeId,
      item.secondaryModeratorNodeId ?? '',
    ].join(':'))
    .sort()
    .join('|')
}

type ModeratorKind = 'w' | 'z' | 'wz'

function moderationKind(
  item: ModelSpec['moderations'][number],
  model: ModelSpec,
): ModeratorKind | null {
  const roleById = new Map(model.nodes.map((node) => [node.id, node.role]))
  const primary = roleById.get(item.moderatorNodeId)
  if (item.secondaryModeratorNodeId) {
    const roles = new Set([primary, roleById.get(item.secondaryModeratorNodeId)])
    return roles.has('w') && roles.has('z') ? 'wz' : null
  }
  return primary === 'w' || primary === 'z' ? primary : null
}

export function ModerationEditor({ model, onChange }: ModerationEditorProps) {
  const presets = presetsFor(model)
  const selectedIds = moderationSignature(model.moderations)
  const wNode = model.nodes.find((node) => node.role === 'w')
  const zNode = model.nodes.find((node) => node.role === 'z')
  const toggleModeration = (edge: ModelEdge, kind: ModeratorKind) => {
    const existing = model.moderations.find(
      (item) => item.targetEdgeId === edge.id && moderationKind(item, model) === kind,
    )
    if (existing) {
      onChange(model.moderations.filter((item) => item.id !== existing.id))
      return
    }
    if ((kind === 'w' || kind === 'wz') && !wNode) return
    if ((kind === 'z' || kind === 'wz') && !zNode) return
    const moderatorNodeId = kind === 'z' ? zNode?.id : wNode?.id
    const secondaryModeratorNodeId = kind === 'wz' ? zNode?.id : undefined
    if (!moderatorNodeId || (kind === 'wz' && !secondaryModeratorNodeId)) return
    const suffix = `${edge.id}_${kind}`.replace(/[^A-Za-z0-9_-]/g, '_').slice(0, 42)
    onChange([
      ...model.moderations,
      {
        id: `mod_${suffix}`,
        moderatorNodeId,
        ...(secondaryModeratorNodeId ? { secondaryModeratorNodeId } : {}),
        targetEdgeId: edge.id,
        productTermId: `term_${suffix}`,
        ...(kind === 'wz' ? { moderatorProductTermId: `term_wz_${suffix}`.slice(0, 63) } : {}),
      },
    ])
  }
  return (
    <section className="moderation-editor" aria-labelledby="moderation-heading">
      <div className="section-heading">
        <div><p className="eyebrow">Moderation map</p><h2 id="moderation-heading">调节变量具体作用于哪一段？</h2></div>
        <span className="selection-count">{model.moderations.length} 条交互项</span>
      </div>
      <p className="muted">选择一个受支持的 PROCESS 结构。画布会从 W/Z 指向被调节路径的中点，不再把调节误画成普通主效应。</p>
      <div className="moderation-target-grid">
        {presets.map((preset) => {
          const presetIds = moderationSignature(presetModerations(model, preset))
          const checked = selectedIds === presetIds
          return (
            <label className={`moderation-target${checked ? ' is-selected' : ''}`} key={preset.id}>
              <input type="radio" name="moderation-preset" checked={checked} onChange={() => onChange(presetModerations(model, preset))} />
              <span className="moderation-target-path">{preset.edges.map((edge) => relationship(edge, model)).join(' + ')}</span>
              <strong>{preset.title}</strong>
              <small>{preset.detail}</small>
            </label>
          )
        })}
      </div>
      <fieldset className="manual-moderation-map">
        <legend>自由构建 · 将调节变量绑定到具体路径</legend>
        <p className="muted">用于反向识别完整 PROCESS 5.0 图鉴。W×Z 表示该路径包含三阶交互。</p>
        <div className="manual-moderation-list">
          {model.edges.map((edge) => (
            <div className="manual-moderation-row" key={edge.id}>
              <strong>{relationship(edge, model)}</strong>
              {(['w', 'z', 'wz'] as const).map((kind) => {
                const unavailable = (kind === 'w' && !wNode)
                  || (kind === 'z' && !zNode)
                  || (kind === 'wz' && (!wNode || !zNode))
                const selected = model.moderations.some(
                  (item) => item.targetEdgeId === edge.id && moderationKind(item, model) === kind,
                )
                return (
                  <button
                    type="button"
                    key={kind}
                    aria-pressed={selected}
                    disabled={unavailable}
                    onClick={() => toggleModeration(edge, kind)}
                  >
                    {kind === 'wz' ? 'W×Z' : kind.toUpperCase()}
                  </button>
                )
              })}
            </div>
          ))}
        </div>
      </fieldset>
      <p className="method-note">Model 21/22 报告 W×Z 的 3×3 条件间接效应网格；Model 58/59 报告同一 W 代表值上的非线性条件间接效应。两类模型均不强行压缩为单一线性“调节中介指数”。</p>
    </section>
  )
}
