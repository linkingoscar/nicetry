import { useState } from 'react'
import type { DatasetVersion, ModelSpec, ModelVariable } from '../../types'
interface SemStudioEstimationPanelProps {
  model: ModelSpec
  variables: ModelVariable[]
  indicatorCandidates: DatasetVersion['variables']
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void
}
export function SemStudioEstimationPanel({
  model,
  variables,
  indicatorCandidates,
  updateModel,
}: SemStudioEstimationPanelProps) {
  const [releaseConstraint, setReleaseConstraint] = useState<'loading' | 'intercept_or_threshold' | 'residual'>('loading')
  const [releaseLatentId, setReleaseLatentId] = useState('')
  const [releaseIndicatorId, setReleaseIndicatorId] = useState('')
  const [releaseRationale, setReleaseRationale] = useState('')
  const firstOrderLatents = (model.latents ?? []).filter((latent) => latent.level !== 'higher_order')
  const selectedReleaseLatent = firstOrderLatents.find((latent) => latent.id === releaseLatentId) ?? firstOrderLatents[0]
  const releaseIndicators = releaseConstraint === 'loading'
    ? selectedReleaseLatent?.indicators ?? []
    : Array.from(new Set(firstOrderLatents.flatMap((latent) => latent.indicators)))
  const selectedReleaseIndicator = releaseIndicators.includes(releaseIndicatorId)
    ? releaseIndicatorId
    : releaseIndicators[0] ?? ''
  const indicatorLabel = (id: string) =>
    indicatorCandidates.find((indicator) => indicator.id === id)?.label ?? id
  return (
    <>
      <label>估计器
        <select value={model.estimation.estimator ?? 'ML'} onChange={(event) => updateModel((current) => ({
          ...current,
          estimation: {
            ...current.estimation,
            estimator: event.target.value as 'ML' | 'WLSMV',
            missing: event.target.value === 'WLSMV' ? 'complete_cases_per_model' : current.estimation.missing,
          },
        }))}>
          <option value="ML">ML 最大似然估计 (连续变量)</option>
          <option value="WLSMV">WLSMV 稳健加权最小二乘 (分类/Likert)</option>
        </select>
      </label>
      {model.estimation.estimator !== 'WLSMV' ? (
        <label>缺失数据处理
          <select value={model.estimation.missing} onChange={(event) => updateModel((current) => ({
            ...current,
            estimation: { ...current.estimation, missing: event.target.value as ModelSpec['estimation']['missing'] },
          }))}>
            <option value="fiml">FIML（保留部分缺失观测）</option>
            <option value="complete_cases_per_model">完整案例删除</option>
          </select>
        </label>
      ) : <p className="method-note">WLSMV 使用有序指标的完整案例口径，不提供 FIML。</p>}
      <label>多组分组变量
        <select value={model.estimation.groupVariableId ?? ''} onChange={(event) => updateModel((current) => ({
          ...current,
          estimation: { ...current.estimation, groupVariableId: event.target.value || null },
        }))}>
          <option value="">不分组</option>
          {variables
            .filter((variable) => variable.dataType === 'binary' || variable.dataType === 'nominal')
            .map((variable) => (
              <option key={variable.id} value={variable.id}>
                {variable.label} ({variable.source})
              </option>
            ))}
        </select>
      </label>
      {model.estimation.groupVariableId ? (
        <fieldset className="sem-option-group">
          <legend>Multi-Group SEM Studio</legend>
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={!!model.estimation.invariance}
              onChange={(event) => updateModel((current) => ({
                ...current,
                estimation: {
                  ...current.estimation,
                  invariance: event.target.checked,
                  multiGroup: event.target.checked
                    ? current.estimation.multiGroup ?? {
                        compareStructuralPaths: false,
                        estimateLatentMeans: false,
                      }
                    : {
                        compareStructuralPaths: false,
                        estimateLatentMeans: false,
                      },
                },
              }))}
            />
            逐级测量等值性（配置、载荷、截距/阈值、残差）
          </label>
          {model.estimation.invariance ? (
            <>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={!!model.estimation.multiGroup?.compareStructuralPaths}
                  onChange={(event) => updateModel((current) => ({
                    ...current,
                    estimation: {
                      ...current.estimation,
                      multiGroup: {
                        ...current.estimation.multiGroup,
                        compareStructuralPaths: event.target.checked,
                        estimateLatentMeans: !!current.estimation.multiGroup?.estimateLatentMeans,
                      },
                    },
                  }))}
                />
                比较结构路径等值模型
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={!!model.estimation.multiGroup?.estimateLatentMeans}
                  onChange={(event) => updateModel((current) => ({
                    ...current,
                    estimation: {
                      ...current.estimation,
                      multiGroup: {
                        ...current.estimation.multiGroup,
                        compareStructuralPaths: !!current.estimation.multiGroup?.compareStructuralPaths,
                        estimateLatentMeans: event.target.checked,
                      },
                    },
                  }))}
                />
                在截距/阈值等值模型中估计潜均值
              </label>
              <details className="sem-measurement-editor">
                <summary>高级约束面板 · 手动部分等值释放</summary>
                <p className="method-note">仅释放有理论依据的少数测量参数。每项理由会进入冻结模型、结果和 APA 表；系统不自动选择释放项。</p>
                <label>释放类型
                  <select
                    value={releaseConstraint}
                    onChange={(event) => {
                      setReleaseConstraint(event.target.value as typeof releaseConstraint)
                      setReleaseIndicatorId('')
                    }}
                  >
                    <option value="loading">载荷（Metric）</option>
                    <option value="intercept_or_threshold">
                      {model.estimation.estimator === 'WLSMV' ? '阈值（Scalar）' : '截距（Scalar）'}
                    </option>
                    <option value="residual">残差（Strict）</option>
                  </select>
                </label>
                {releaseConstraint === 'loading' ? (
                  <label>潜变量
                    <select
                      value={selectedReleaseLatent?.id ?? ''}
                      onChange={(event) => {
                        setReleaseLatentId(event.target.value)
                        setReleaseIndicatorId('')
                      }}
                    >
                      {firstOrderLatents.map((latent) => (
                        <option key={latent.id} value={latent.id}>{latent.name}</option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <label>观测指标
                  <select value={selectedReleaseIndicator} onChange={(event) => setReleaseIndicatorId(event.target.value)}>
                    {releaseIndicators.map((indicatorId) => (
                      <option key={indicatorId} value={indicatorId}>{indicatorLabel(indicatorId)}</option>
                    ))}
                  </select>
                </label>
                <label>理论或探索性理由（至少 8 个字符）
                  <textarea
                    value={releaseRationale}
                    onChange={(event) => setReleaseRationale(event.target.value)}
                    placeholder="例如：该题项在两组中的措辞语境不同，按预设敏感性分析释放。"
                  />
                </label>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={!selectedReleaseIndicator || releaseRationale.trim().length < 8}
                  onClick={() => {
                    const stage = releaseConstraint === 'loading'
                      ? 'metric'
                      : releaseConstraint === 'residual'
                        ? 'strict'
                        : 'scalar'
                    updateModel((current) => ({
                      ...current,
                      estimation: {
                        ...current.estimation,
                        multiGroup: {
                          compareStructuralPaths: !!current.estimation.multiGroup?.compareStructuralPaths,
                          estimateLatentMeans: !!current.estimation.multiGroup?.estimateLatentMeans,
                          partialInvarianceReleases: [
                            ...(current.estimation.multiGroup?.partialInvarianceReleases ?? []),
                            {
                              stage,
                              constraint: releaseConstraint,
                              latentId: releaseConstraint === 'loading' ? selectedReleaseLatent?.id ?? null : null,
                              indicatorId: selectedReleaseIndicator,
                              rationale: releaseRationale.trim(),
                            },
                          ],
                        },
                      },
                    }))
                    setReleaseRationale('')
                  }}
                >
                  添加手动释放
                </button>
                {(model.estimation.multiGroup?.partialInvarianceReleases?.length ?? 0) > 0 ? (
                  <ul>
                    {model.estimation.multiGroup?.partialInvarianceReleases?.map((release, index) => (
                      <li key={`${release.stage}:${release.constraint}:${release.latentId}:${release.indicatorId}:${release.rationale}`}>
                        {release.stage} · {release.constraint} · {indicatorLabel(release.indicatorId)}
                        <button
                          type="button"
                          className="secondary-button"
                          onClick={() => updateModel((current) => ({
                            ...current,
                            estimation: {
                              ...current.estimation,
                              multiGroup: {
                                compareStructuralPaths: !!current.estimation.multiGroup?.compareStructuralPaths,
                                estimateLatentMeans: !!current.estimation.multiGroup?.estimateLatentMeans,
                                partialInvarianceReleases: current.estimation.multiGroup?.partialInvarianceReleases?.filter((_, releaseIndex) => releaseIndex !== index),
                              },
                            },
                          }))}
                        >
                          移除
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </details>
            </>
          ) : null}
        </fieldset>
      ) : null}
    </>
  )
}
