import { useMemo, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

import { saveMeasurement } from '../api'
import type {
  ConstructDraft,
  DatasetVariable,
  MeasurementVersion,
} from '../types'
import { MeasurementWorkspaceResults } from './MeasurementWorkspaceResults'
import { draftsFromMeasurement, newConstruct } from './measurementWorkspaceUtils'
import styles from './MeasurementWorkspace.module.css'

interface MeasurementWorkspaceProps {
  datasetId: string
  variables: DatasetVariable[]
  initialMeasurement?: MeasurementVersion
  onReady?: (measurement: MeasurementVersion) => void
}

export function MeasurementWorkspace({
  datasetId,
  variables,
  initialMeasurement,
  onReady,
}: MeasurementWorkspaceProps) {
  const [constructs, setConstructs] = useState<ConstructDraft[]>(() =>
    draftsFromMeasurement(initialMeasurement),
  )
  const nextConstructSequence = useRef((initialMeasurement?.constructs.length ?? 1) + 1)
  const [changeNote, setChangeNote] = useState(initialMeasurement?.changeNote ?? '')
  const [formError, setFormError] = useState<string | null>(null)
  const candidates = useMemo(
    () => variables.filter((variable) =>
      ['likert', 'ordinal', 'continuous'].includes(variable.confirmedType ?? variable.inferredType),
    ),
    [variables],
  )
  const measurementMutation = useMutation({
    mutationFn: (definitions: ConstructDraft[]) => saveMeasurement(datasetId, definitions, changeNote),
    onSuccess: (measurement) => onReady?.(measurement),
  })

  const updateConstruct = (id: string, update: Partial<ConstructDraft>) => {
    measurementMutation.reset()
    setConstructs((current) => current.map((construct) =>
      construct.id === id ? { ...construct, ...update } : construct,
    ))
  }

  const toggleItem = (construct: ConstructDraft, itemId: string) => {
    const selected = construct.itemIds.includes(itemId)
    updateConstruct(construct.id, {
      itemIds: selected
        ? construct.itemIds.filter((id) => id !== itemId)
        : [...construct.itemIds, itemId],
      reverseItemIds: selected
        ? construct.reverseItemIds.filter((id) => id !== itemId)
        : construct.reverseItemIds,
    })
  }

  const toggleReverse = (construct: ConstructDraft, itemId: string) => {
    updateConstruct(construct.id, {
      reverseItemIds: construct.reverseItemIds.includes(itemId)
        ? construct.reverseItemIds.filter((id) => id !== itemId)
        : [...construct.reverseItemIds, itemId],
    })
  }

  const handleSave = () => {
    const invalid = constructs.find((construct) =>
      !construct.name.trim()
      || construct.itemIds.length < 2
      || construct.theoreticalMinimum >= construct.theoreticalMaximum,
    )
    if (invalid) {
      setFormError('每个构念都需要名称、至少两个题项，以及有效的理论上下限。')
      return
    }
    setFormError(null)
    measurementMutation.mutate(constructs)
  }

  const measurement = measurementMutation.data ?? initialMeasurement

  return (
    <section className="measurement-workspace" aria-labelledby="measurement-heading">
      <div className="section-heading dictionary-heading-row">
        <div>
          <p className="eyebrow">量表</p>
          <h2 id="measurement-heading">构念与量表</h2>
          <p className="muted">分组题项、确认理论量尺、设置反向题和有效题项规则。保存后生成新的派生数据版本。</p>
        </div>
        <div className={styles.workspaceActions}>
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              if (window.confirm('确定要清空并重置当前未冻结的构念草稿吗？')) {
                nextConstructSequence.current = (initialMeasurement?.constructs.length ?? 1) + 1
                measurementMutation.reset()
                setConstructs(draftsFromMeasurement(initialMeasurement))
                setFormError(null)
              }
            }}
            title="清空当前未冻结草稿"
          >
            🧹 重置草稿
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => {
              const sequence = nextConstructSequence.current
              nextConstructSequence.current += 1
              measurementMutation.reset()
              setConstructs((current) => [...current, newConstruct(sequence)])
            }}
          >
            添加构念
          </button>
        </div>
      </div>

      {candidates.length < 2 ? (
        <p className="method-warning">至少需要两个可用的 Likert、有序或连续变量，才能建立构念；无需先确认所有无关变量。</p>
      ) : null}

      <div className="construct-list">
        {constructs.map((construct, index) => {
          const assignedElsewhere = new Set(
            constructs.filter((other) => other.id !== construct.id).flatMap((other) => other.itemIds),
          )
          return (
            <article className="construct-card" key={construct.id}>
              <div className="construct-title-row">
                <strong>构念 {index + 1}</strong>
                {constructs.length > 1 ? (
                  <button
                    className="text-button"
                    type="button"
                    onClick={() => {
                      measurementMutation.reset()
                      setConstructs((current) => current.filter((item) => item.id !== construct.id))
                    }}
                  >删除</button>
                ) : null}
              </div>
              <div className="construct-settings">
                <label>构念名称
                  <input
                    aria-label={`构念 ${index + 1} 名称`}
                    value={construct.name}
                    onChange={(event) => updateConstruct(construct.id, { name: event.target.value })}
                    placeholder="例如：工作投入"
                  />
                </label>
                <label>理论最小值
                  <input
                    type="number"
                    value={construct.theoreticalMinimum}
                    onChange={(event) => updateConstruct(construct.id, { theoreticalMinimum: Number(event.target.value) })}
                  />
                </label>
                <label>理论最大值
                  <input
                    type="number"
                    value={construct.theoreticalMaximum}
                    onChange={(event) => updateConstruct(construct.id, { theoreticalMaximum: Number(event.target.value) })}
                  />
                </label>
                <label>合成方式
                  <select
                    value={construct.aggregation}
                    onChange={(event) => updateConstruct(construct.id, { aggregation: event.target.value as 'mean' | 'sum' })}
                  >
                    <option value="mean">有效题项均分</option>
                    <option value="sum">有效题项总分</option>
                  </select>
                </label>
                <label>最少有效题项比例
                  <input
                    type="number"
                    min="0.01"
                    max="1"
                    step="0.05"
                    value={construct.minimumValidProportion}
                    onChange={(event) => updateConstruct(construct.id, { minimumValidProportion: Number(event.target.value) })}
                  />
                </label>
              </div>
              <fieldset className="item-picker">
                <legend className="sr-only">{`${construct.name || `构念 ${index + 1}`}题项`}</legend>
                <div className="item-picker-heading"><span>纳入题项</span><span>反向</span></div>
                {candidates.map((variable) => {
                  const selected = construct.itemIds.includes(variable.id)
                  const unavailable = assignedElsewhere.has(variable.id)
                  return (
                    <div className="item-picker-row" key={variable.id}>
                      <label>
                        <input
                          type="checkbox"
                          checked={selected}
                          disabled={unavailable}
                          onChange={() => toggleItem(construct, variable.id)}
                        />
                        <span>{variable.label}</span>
                        <small>{variable.originalName}</small>
                      </label>
                      <input
                        aria-label={`${variable.label}反向计分`}
                        type="checkbox"
                        checked={construct.reverseItemIds.includes(variable.id)}
                        disabled={!selected}
                        onChange={() => toggleReverse(construct, variable.id)}
                      />
                    </div>
                  )
                })}
              </fieldset>
            </article>
          )
        })}
      </div>

      {formError ? <p className="error-message error-banner" role="alert">{formError}</p> : null}
      {measurementMutation.error ? <p className="error-message error-banner" role="alert">{measurementMutation.error.message}</p> : null}
      <label className="change-note">版本说明 / 删题依据
        <textarea
          value={changeNote}
          maxLength={500}
          onChange={(event) => setChangeNote(event.target.value)}
          placeholder="首次建立可留空；删除既有题项或构念时必须说明理论与统计依据。"
        />
      </label>
      <button
        className="run-button measurement-save"
        type="button"
        disabled={measurementMutation.isPending || candidates.length < 2}
        onClick={handleSave}
      >
        {measurementMutation.isPending ? '正在计分和测量检查…' : '保存规则并生成量表版本'}
      </button>

      {measurement ? <MeasurementWorkspaceResults measurement={measurement} /> : null}
    </section>
  )
}
