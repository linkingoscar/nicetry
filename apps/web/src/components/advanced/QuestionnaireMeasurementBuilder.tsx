import type { QuestionnaireMeasurementSpec } from '../../types/advanced'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

interface QuestionnaireMeasurementBuilderProps {
  spec: QuestionnaireMeasurementSpec
  variables?: DatasetVariableItem[]
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

export function QuestionnaireMeasurementBuilder({
  spec,
  variables = [],
  onChange,
}: QuestionnaireMeasurementBuilderProps) {
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
          <select
            value={spec.modelType}
            onChange={event => {
              const modelType = event.target.value as QuestionnaireMeasurementSpec['modelType']
              if (modelType === 'irt') {
                update({ modelType, itemScale: 'ordinal', estimator: 'MML', irtModel: 'auto' })
              }
              else if (modelType === 'esem' || modelType === 'esem_bifactor_irt') {
                update({ modelType, itemScale: 'continuous', estimator: 'ML', rotation: 'target', factorCount: spec.constructs.length })
              }
              else {
                update({ modelType, estimator: spec.estimator === 'MML' ? (spec.itemScale === 'ordinal' ? 'WLSMV' : 'ML') : spec.estimator })
              }
            }}
          >
            {MODEL_TYPES.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        <label>
          <span>题项量尺</span>
          <select
            value={spec.itemScale}
            onChange={event => {
              const itemScale = event.target.value as QuestionnaireMeasurementSpec['itemScale']
              update({ itemScale, estimator: spec.modelType === 'irt' ? 'MML' : itemScale === 'ordinal' ? 'WLSMV' : ['WLSMV', 'MML'].includes(spec.estimator) ? 'ML' : spec.estimator })
            }}
          >
            <option value="continuous">连续题项</option>
            <option value="ordinal">有序题项</option>
          </select>
        </label>
        <label>
          <span>估计器</span>
          <select value={spec.estimator} onChange={event => update({ estimator: event.target.value as QuestionnaireMeasurementSpec['estimator'] })} disabled={spec.itemScale === 'ordinal' || spec.modelType === 'irt'}>
            <option value="ML">ML</option>
            <option value="MLR">MLR</option>
            <option value="WLSMV">WLSMV</option>
            <option value="MML">MML（IRT）</option>
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
            <option value="target">TargetQ（按构念生成目标矩阵）</option>
          </select>
        </label>
        {spec.modelType === 'irt' && (
          <label>
            <span>IRT 模型</span>
            <select value={spec.irtModel ?? 'auto'} onChange={event => update({ irtModel: event.target.value as NonNullable<QuestionnaireMeasurementSpec['irtModel']> })}>
              <option value="auto">自动：二元 2PL / 多分类 GRM</option>
              <option value="2PL">二元 2PL</option>
              <option value="GRM">多分类 GRM</option>
            </select>
          </label>
        )}
        <label>
          <span>分组变量（可选）</span>
          <select value={spec.groupVariableId ?? ''} onChange={event => update({ groupVariableId: event.target.value || null })}>
            <option value="">不分组</option>
            {variables.filter(variable => variable.type === 'categorical').map(variable => (
              <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>
            ))}
          </select>
        </label>
        {(spec.modelType === 'marker_variable' || spec.modelType === 'common_method_bias') && (
          <label>
            <span>Marker 变量</span>
            <select value={spec.markerVariableId ?? ''} onChange={event => update({ markerVariableId: event.target.value || null })}>
              <option value="">请选择</option>
              {variables.map(variable => (
                <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>
              ))}
            </select>
          </label>
        )}
        <div className="adv-builder-span-2">
          <DatasetVariablePicker
            label="测量题项"
            roleHint="可多选"
            variables={variables.filter(variable => variable.type === 'numeric' || variable.type === 'categorical')}
            selectedIds={spec.itemIds}
            onChange={itemIds => update({
              itemIds,
              constructs: spec.constructs.map(construct => ({
                ...construct,
                itemIds: construct.itemIds.filter(itemId => itemIds.includes(itemId)),
              })),
            })}
            isMulti
          />
        </div>
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
            <div className="adv-builder-construct-items">
              <DatasetVariablePicker
                label="题项"
                variables={variables.filter(variable => spec.itemIds.includes(variable.id))}
                selectedIds={construct.itemIds}
                onChange={itemIds => updateConstruct(index, { itemIds })}
                isMulti
              />
            </div>
            <button type="button" className="adv-btn-danger" onClick={() => removeConstruct(index)} disabled={spec.constructs.length <= 2}>删除</button>
          </div>
        ))}
      </div>
    </section>
  )
}
