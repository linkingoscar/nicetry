import { useEffect } from 'react'
import type { QuestionnaireMeasurementSpec } from '../../types/advanced'
import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

interface QuestionnaireMeasurementBuilderProps {
  spec: QuestionnaireMeasurementSpec
  variables?: DatasetVariableItem[]
  onChange: (spec: QuestionnaireMeasurementSpec) => void
  sliceId?: string
}

type MeasurementConstruct = QuestionnaireMeasurementSpec['constructs'][number]
type MeasurementModelType = QuestionnaireMeasurementSpec['modelType']

const MODEL_TYPES: Array<{ value: MeasurementModelType; label: string }> = [
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

const MODEL_TYPES_BY_SLICE: Record<string, MeasurementModelType[]> = {
  'questionnaire_measurement.reliability': ['reliability'],
  'questionnaire_measurement.efa': ['efa'],
  'questionnaire_measurement.cfa': ['cfa'],
  'questionnaire_measurement.measurement_invariance': ['measurement_invariance'],
  'questionnaire_measurement.esem_bifactor_irt': ['esem_bifactor_irt', 'bifactor', 'esem', 'irt'],
  'questionnaire_measurement.common_method_bias': ['common_method_bias', 'marker_variable', 'ulmc'],
}

export function measurementModelTypesForSlice(sliceId?: string): MeasurementModelType[] {
  return sliceId && MODEL_TYPES_BY_SLICE[sliceId]
    ? MODEL_TYPES_BY_SLICE[sliceId]
    : MODEL_TYPES.map((option) => option.value)
}

function applyMeasurementModelType(
  spec: QuestionnaireMeasurementSpec,
  modelType: MeasurementModelType,
): QuestionnaireMeasurementSpec {
  if (modelType === 'irt') {
    return { ...spec, modelType, itemScale: 'ordinal', estimator: 'MML', irtModel: 'auto' }
  }
  if (modelType === 'esem' || modelType === 'esem_bifactor_irt') {
    return {
      ...spec,
      modelType,
      itemScale: 'continuous',
      estimator: 'ML',
      rotation: 'target',
      factorCount: spec.constructs.length,
    }
  }
  return {
    ...spec,
    modelType,
    estimator: spec.estimator === 'MML'
      ? (spec.itemScale === 'ordinal' ? 'WLSMV' : 'ML')
      : spec.estimator,
  }
}

export function normalizeMeasurementSpecForSlice(
  spec: QuestionnaireMeasurementSpec,
  sliceId?: string,
): QuestionnaireMeasurementSpec {
  const allowed = measurementModelTypesForSlice(sliceId)
  return allowed.includes(spec.modelType) ? spec : applyMeasurementModelType(spec, allowed[0])
}

export function QuestionnaireMeasurementBuilder({
  spec,
  variables = [],
  onChange,
  sliceId,
}: QuestionnaireMeasurementBuilderProps) {
  const normalizedSpec = normalizeMeasurementSpecForSlice(spec, sliceId)
  const allowedModelTypes = measurementModelTypesForSlice(sliceId)
  const modelOptions = MODEL_TYPES.filter((option) => allowedModelTypes.includes(option.value))

  useEffect(() => {
    if (JSON.stringify(normalizedSpec) !== JSON.stringify(spec)) onChange(normalizedSpec)
  }, [normalizedSpec, onChange, spec])

  const update = (patch: Partial<QuestionnaireMeasurementSpec>) => onChange({ ...normalizedSpec, ...patch })
  const updateConstruct = (index: number, patch: Partial<MeasurementConstruct>) => {
    const constructs = normalizedSpec.constructs.map((construct, constructIndex) => (
      constructIndex === index ? { ...construct, ...patch } : construct
    ))
    update({ constructs })
  }
  const addConstruct = () => {
    const nextIndex = normalizedSpec.constructs.length + 1
    update({
      constructs: [
        ...normalizedSpec.constructs,
        { id: `construct_${nextIndex}`, label: `构念 ${nextIndex}`, itemIds: [] },
      ],
    })
  }
  const removeConstruct = (index: number) => {
    if (normalizedSpec.constructs.length <= 2) return
    update({ constructs: normalizedSpec.constructs.filter((_, constructIndex) => constructIndex !== index) })
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
            value={normalizedSpec.modelType}
            disabled={allowedModelTypes.length === 1}
            onChange={event => onChange(applyMeasurementModelType(
              normalizedSpec,
              event.target.value as MeasurementModelType,
            ))}
          >
            {modelOptions.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
          {sliceId ? (
            <small className="adv-field-help">
              {allowedModelTypes.length === 1
                ? '当前方法由方法库入口锁定；切换测量方法请返回方法库。'
                : '当前入口只允许该高级方法组内的已登记变体。'}
            </small>
          ) : null}
        </label>
        <label>
          <span>题项量尺</span>
          <select
            value={normalizedSpec.itemScale}
            onChange={event => {
              const itemScale = event.target.value as QuestionnaireMeasurementSpec['itemScale']
              update({ itemScale, estimator: normalizedSpec.modelType === 'irt' ? 'MML' : itemScale === 'ordinal' ? 'WLSMV' : ['WLSMV', 'MML'].includes(normalizedSpec.estimator) ? 'ML' : normalizedSpec.estimator })
            }}
          >
            <option value="continuous">连续题项</option>
            <option value="ordinal">有序题项</option>
          </select>
        </label>
        <label>
          <span>估计器</span>
          <select value={normalizedSpec.estimator} onChange={event => update({ estimator: event.target.value as QuestionnaireMeasurementSpec['estimator'] })} disabled={normalizedSpec.itemScale === 'ordinal' || normalizedSpec.modelType === 'irt'}>
            <option value="ML">ML</option>
            <option value="MLR">MLR</option>
            <option value="WLSMV">WLSMV</option>
            <option value="MML">MML（IRT）</option>
          </select>
        </label>
        <label>
          <span>因子数</span>
          <input type="number" min={1} max={20} value={normalizedSpec.factorCount} onChange={event => update({ factorCount: Number(event.target.value) || 1 })} />
        </label>
        <label>
          <span>旋转</span>
          <select value={normalizedSpec.rotation} onChange={event => update({ rotation: event.target.value as QuestionnaireMeasurementSpec['rotation'] })}>
            <option value="promax">Promax</option>
            <option value="varimax">Varimax</option>
            <option value="target">TargetQ（按构念生成目标矩阵）</option>
          </select>
        </label>
        {normalizedSpec.modelType === 'irt' && (
          <label>
            <span>IRT 模型</span>
            <select value={normalizedSpec.irtModel ?? 'auto'} onChange={event => update({ irtModel: event.target.value as NonNullable<QuestionnaireMeasurementSpec['irtModel']> })}>
              <option value="auto">自动：二元 2PL / 多分类 GRM</option>
              <option value="2PL">二元 2PL</option>
              <option value="GRM">多分类 GRM</option>
            </select>
          </label>
        )}
        <label>
          <span>分组变量（可选）</span>
          <select value={normalizedSpec.groupVariableId ?? ''} onChange={event => update({ groupVariableId: event.target.value || null })}>
            <option value="">不分组</option>
            {variables.filter(variable => variable.type === 'categorical').map(variable => (
              <option key={variable.id} value={variable.id}>{variable.label || variable.name}</option>
            ))}
          </select>
        </label>
        {(normalizedSpec.modelType === 'marker_variable' || normalizedSpec.modelType === 'common_method_bias') && (
          <label>
            <span>Marker 变量</span>
            <select value={normalizedSpec.markerVariableId ?? ''} onChange={event => update({ markerVariableId: event.target.value || null })}>
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
            selectedIds={normalizedSpec.itemIds}
            onChange={itemIds => update({
              itemIds,
              constructs: normalizedSpec.constructs.map(construct => ({
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
        {normalizedSpec.constructs.map((construct, index) => (
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
                variables={variables.filter(variable => normalizedSpec.itemIds.includes(variable.id))}
                selectedIds={construct.itemIds}
                onChange={itemIds => updateConstruct(index, { itemIds })}
                isMulti
              />
            </div>
            <button type="button" className="adv-btn-danger" onClick={() => removeConstruct(index)} disabled={normalizedSpec.constructs.length <= 2}>删除</button>
          </div>
        ))}
      </div>
    </section>
  )
}
