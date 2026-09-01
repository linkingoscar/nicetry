import type { QuestionnaireMeasurementSpec } from '../../types/advanced'

interface QuestionnaireMeasurementBuilderProps {
  spec: QuestionnaireMeasurementSpec
  onChange: (spec: QuestionnaireMeasurementSpec) => void
}

type MeasurementConstruct = QuestionnaireMeasurementSpec['constructs'][number]

const MODEL_TYPES: Array<{ value: QuestionnaireMeasurementSpec['modelType']; label: string }> = [
  { value: 'reliability', label: '信度（α / ω）' },
  { value: 'efa', label: '探索性因子分析（EFA）' },
  { value: 'cfa', label: '验证性因子分析（CFA）' },
  { value: 'measurement_invariance', label: '测量不变性' },
  { value: 'esem_bifactor_irt', label: 'ESEM / Bifactor / IRT' },
  { value: 'bifactor', label: 'Bifactor' },
  { value: 'esem', label: 'ESEM' },
  { value: 'irt', label: 'IRT / DIF' },
  { value: 'common_method_bias', label: '共同方法偏差（CMB）' },
  { value: 'marker_variable', label: 'Marker Variable' },
  { value: 'ulmc', label: '未测量潜方法因子（ULMC）' },
]

function splitIds(value: string): string[] {
  return Array.from(new Set(value.split(/[,，\s]+/).map(item => item.trim()).filter(Boolean)))
}

function constructIds(construct: MeasurementConstruct): string {
  return construct.itemIds.join(', ')
}

export function QuestionnaireMeasurementBuilder({ spec, onChange }: QuestionnaireMeasurementBuilderProps) {
  const update = (patch: Partial<QuestionnaireMeasurementSpec>) => onChange({ ...spec, ...patch })
  const updateConstruct = (index: number, patch: Partial<MeasurementConstruct>) => {
    const constructs = spec.constructs.map((construct, constructIndex) => (
      constructIndex === index ? { ...construct, ...patch } : construct
    ))
    update({ constructs })
  }
  const addConstruct = () => {
    const nextIndex = spec.constructs.length + 1
    update({
      constructs: [
        ...spec.constructs,
        { id: `construct_${nextIndex}`, label: `构念 ${nextIndex}`, itemIds: [] },
      ],
    })
  }
  const removeConstruct = (index: number) => {
    if (spec.constructs.length <= 2) return
    update({ constructs: spec.constructs.filter((_, constructIndex) => constructIndex !== index) })
  }

  return (
    <section className="adv-measurement-builder" aria-label="问卷测量配置">
      <div className="adv-builder-intro">
        <h3>问卷测量配置</h3>
        <p className="muted">使用字段化配置声明题项、构念、量尺和分组变量；验证摘要会显示最终提交规格。</p>
      </div>

      <div className="adv-builder-grid">
        <label>
          <span>测量方法</span>
          <select value={spec.modelType} onChange={event => update({ modelType: event.target.value as QuestionnaireMeasurementSpec['modelType'] })}>
            {MODEL_TYPES.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          <span>题项量尺</span>
          <select
            value={spec.itemScale}
            onChange={event => {
              const itemScale = event.target.value as QuestionnaireMeasurementSpec['itemScale']
              update({ itemScale, estimator: itemScale === 'ordinal' ? 'WLSMV' : spec.estimator === 'WLSMV' ? 'ML' : spec.estimator })
            }}
          >
            <option value="continuous">连续题项</option>
            <option value="ordinal">有序题项</option>
          </select>
        </label>
        <label>
          <span>估计器</span>
          <select value={spec.estimator} onChange={event => update({ estimator: event.target.value as QuestionnaireMeasurementSpec['estimator'] })} disabled={spec.itemScale === 'ordinal'}>
            <option value="ML">ML</option>
            <option value="MLR">MLR</option>
            <option value="WLSMV">WLSMV</option>
          </select>
        </label>
        <label>
          <span>因子数</span>
          <input type="number" min={1} max={20} value={spec.factorCount} onChange={event => update({ factorCount: Number(event.target.value) || 1 })} />
        </label>
        <label>
          <span>旋转</span>
          <select value={spec.rotation} onChange={event => update({ rotation: event.target.value as QuestionnaireMeasurementSpec['rotation'] })}>
            <option value="promax">Promax</option>
            <option value="varimax">Varimax</option>
          </select>
        </label>
        <label>
          <span>分组变量（可选）</span>
          <input value={spec.groupVariableId ?? ''} onChange={event => update({ groupVariableId: event.target.value.trim() || null })} placeholder="例如 group" />
        </label>
        {(spec.modelType === 'marker_variable' || spec.modelType === 'common_method_bias') && (
          <label>
            <span>Marker 变量</span>
            <input value={spec.markerVariableId ?? ''} onChange={event => update({ markerVariableId: event.target.value.trim() || null })} placeholder="例如 marker" />
          </label>
        )}
        <label className="adv-builder-span-2">
          <span>题项 ID（逗号或空格分隔）</span>
          <input value={spec.itemIds.join(', ')} onChange={event => update({ itemIds: splitIds(event.target.value) })} placeholder="item_1, item_2, item_3" />
        </label>
      </div>

      <div className="adv-builder-constructs">
        <div className="adv-builder-section-header">
          <div>
            <h4>构念与题项归属</h4>
            <p className="muted">每个构念至少需要两个题项；题项必须属于上面的题项列表。</p>
          </div>
          <button type="button" className="adv-btn-secondary" onClick={addConstruct}>增加构念</button>
        </div>
        {spec.constructs.map((construct, index) => (
          <div className="adv-construct-row" key={construct.id}>
            <label>
              <span>ID</span>
              <input value={construct.id} onChange={event => updateConstruct(index, { id: event.target.value })} />
            </label>
            <label>
              <span>标签</span>
              <input value={construct.label} onChange={event => updateConstruct(index, { label: event.target.value })} />
            </label>
            <label className="adv-builder-construct-items">
              <span>题项</span>
              <input value={constructIds(construct)} onChange={event => updateConstruct(index, { itemIds: splitIds(event.target.value) })} placeholder="item_1, item_2" />
            </label>
            <button type="button" className="adv-btn-danger" onClick={() => removeConstruct(index)} disabled={spec.constructs.length <= 2}>删除</button>
          </div>
        ))}
      </div>
    </section>
  )
}
