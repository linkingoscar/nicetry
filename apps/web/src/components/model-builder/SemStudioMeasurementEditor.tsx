import { useEffect, useState } from 'react'

import type { DatasetVersion, ModelSpec } from '../../types'
import styles from './SemStudio.module.css'
import { removeStructuralNodeModel } from './modelStructureActions'
import { removeLatentDefinitions } from './semModelIntegrity'

interface SemStudioMeasurementEditorProps {
  model: ModelSpec
  indicatorCandidates: DatasetVersion['variables']
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void
  focusedLatentId?: string | null
}

export function SemStudioMeasurementEditor({
  model,
  indicatorCandidates,
  updateModel,
  focusedLatentId,
}: SemStudioMeasurementEditorProps) {
  const [newHigherOrderName, setNewHigherOrderName] = useState('总体构念')
  const firstOrderLatents = (model.latents ?? []).filter((latent) => latent.level !== 'higher_order')
  useEffect(() => {
    if (focusedLatentId) document.getElementById(`sem-measurement-${focusedLatentId}`)?.focus()
  }, [focusedLatentId])

  return (
    <div className="sem-measurement-editor">
      <strong>潜变量与测量指标</strong>
      {(model.latents ?? []).length === 0 ? (
        <p className="method-warning">当前结构节点没有匹配到已计分构念。请返回“数据与测量”定义构念，或改用观测变量路径模型。</p>
      ) : (model.latents ?? []).map((latent) => (
        <details key={latent.id} open={focusedLatentId === latent.id ? true : undefined}>
          <summary id={`sem-measurement-${latent.id}`} tabIndex={0}>
            {latent.name} · {latent.indicators.length} 个
            {latent.level === 'higher_order' ? '低阶因子' : '题项指标'}
            {latent.level === 'higher_order' ? ' · 高阶' : ''}
          </summary>
          <label>潜变量名称
            <input value={latent.name} onChange={(event) => updateModel((current) => ({
              ...current,
              nodes: current.nodes.map((node) => node.id === latent.id
                ? { ...node, label: event.target.value }
                : node),
              latents: current.latents?.map((item) => item.id === latent.id
                ? { ...item, name: event.target.value }
                : item),
            }))} />
          </label>
          <fieldset className="sem-option-group">
            <legend>{latent.level === 'higher_order' ? '低阶潜变量（至少 3 个）' : '测量指标（至少 2 个）'}</legend>
            {(latent.level === 'higher_order'
              ? (model.latents ?? [])
                  .filter((candidate) => candidate.id !== latent.id)
                  .map((candidate) => ({
                    id: candidate.id,
                    label: candidate.name,
                    originalName: candidate.level === 'higher_order' ? '高阶潜变量' : '一阶潜变量',
                  }))
              : indicatorCandidates
            ).map((indicator) => {
              const checked = latent.indicators.includes(indicator.id)
              return (
                <label className="checkbox-label" key={`${latent.id}-${indicator.id}`}>
                  <input type="checkbox" checked={checked} onChange={() => updateModel((current) => removeLatentDefinitions({
                    ...current,
                    latents: current.latents?.map((item) => item.id === latent.id
                      ? {
                          ...item,
                          indicators: checked
                            ? item.indicators.filter((id) => id !== indicator.id)
                            : [...item.indicators, indicator.id],
                        }
                      : item),
                  }, []))} />
                  {indicator.label} ({indicator.originalName})
                </label>
              )
            })}
          </fieldset>
          <button type="button" className="secondary" onClick={() => updateModel((current) => removeStructuralNodeModel(current, latent.id))}>
              删除该{latent.level === 'higher_order' ? '高阶' : ''}潜变量
            </button>
          {!model.nodes.some(node => node.id === latent.id) ? <button type="button" className="secondary" onClick={() => updateModel(current => ({
            ...current, nodes: [...current.nodes, { id: latent.id, label: latent.name, kind: 'latent', role: 'm', dataType: 'continuous' }],
          }))}>加入结构图（随后连接路径）</button> : null}
        </details>
      ))}
      <div className={`inline-form ${styles.inlineForm}`}>
        <label>新建高阶潜变量
          <input
            value={newHigherOrderName}
            onChange={(event) => setNewHigherOrderName(event.target.value)}
            placeholder="例如：总体领导力"
          />
        </label>
        <button
          type="button"
          className="secondary"
          disabled={firstOrderLatents.length < 3}
          onClick={() => updateModel((current) => {
            const lowerOrder = (current.latents ?? []).filter((latent) => latent.level !== 'higher_order')
            let suffix = (current.latents ?? []).length + 1
            while ((current.latents ?? []).some(latent => latent.id === `higher_factor_${suffix}`) || current.nodes.some(node => node.id === `higher_factor_${suffix}`)) suffix += 1
            return {
              ...current,
              latents: [
                ...(current.latents ?? []),
                {
                  id: `higher_factor_${suffix}`,
                  name: newHigherOrderName.trim() || `高阶潜变量 ${suffix}`,
                  level: 'higher_order',
                  indicators: lowerOrder.map((latent) => latent.id),
                },
              ],
            }
          })}
        >
          添加高阶潜变量
        </button>
      </div>
      <button type="button" className="secondary" onClick={() => updateModel(current => {
        let suffix = 1
        while ((current.latents ?? []).some(latent => latent.id === `factor_${suffix}`) || current.nodes.some(node => node.id === `factor_${suffix}`)) suffix += 1
        return { ...current, latents: [...(current.latents ?? []), { id: `factor_${suffix}`, name: `新因子 ${suffix}`, level: 'first_order', indicators: [] }] }
      })}>添加测量因子</button>
      <p className="method-note">高阶潜变量以低阶潜变量为指标；冻结前会检查指标数、变量存在性、层级循环、分组数量与模型识别条件。</p>
    </div>
  )
}
