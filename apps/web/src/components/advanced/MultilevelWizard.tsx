import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

export interface MultilevelWizardSpec {
  family: 'multilevel_model'
  datasetVersionId?: string
  analysisType: 'lmm' | 'aggregation'
  outcomeId?: string | null
  distribution: 'gaussian'
  clusterVariableId: string
  fixedEffectIds: string[]
  randomEffects: Array<{
    groupingVariableId: string
    intercept: boolean
    slopeVariableIds: string[]
    covariance: 'correlated' | 'diagonal'
  }>
  centering: Array<{ variableId: string; method: 'none' | 'grand_mean' | 'group_mean' }>
  estimator: 'REML' | 'ML' | 'MLR'
  degreesOfFreedom: 'satterthwaite' | 'kenward_roger' | 'asymptotic'
  minimumClusterCount: number
  scaleItemIds: string[]
  scaleMin: number
  scaleMax: number
  aggregationMethod: 'mean' | 'sum'
}

interface MultilevelWizardProps {
  spec: MultilevelWizardSpec
  onChange: (spec: MultilevelWizardSpec) => void
  variables: DatasetVariableItem[]
  sliceId?: string
}

export function multilevelAnalysisTypeForSlice(sliceId?: string): MultilevelWizardSpec['analysisType'] | undefined {
  if (sliceId?.includes('.aggregation.')) return 'aggregation'
  if (sliceId?.includes('.gaussian.')) return 'lmm'
  return undefined
}

export function MultilevelWizard({ spec, onChange, variables, sliceId }: MultilevelWizardProps) {
  const update = (patch: Partial<MultilevelWizardSpec>) => onChange({ ...spec, ...patch })
  const lockedAnalysisType = multilevelAnalysisTypeForSlice(sliceId)
  const analysisType = lockedAnalysisType ?? spec.analysisType
  const randomEffects = spec.randomEffects ?? []
  const centering = spec.centering ?? []

  const clusterCandidates = variables.filter(variable => (
    variable.id === spec.clusterVariableId
    || variable.recommendedRoles?.includes('cluster')
    || variable.type !== 'datetime'
  ))
  const numericVariables = variables.filter(variable => variable.type === 'numeric')
  const scaleCandidates = variables.filter(variable => (
    variable.id !== spec.clusterVariableId
    && variable.type !== 'datetime'
    && variable.type !== 'text'
  ))

  const updateCluster = (clusterVariableId: string) => {
    update({
      clusterVariableId,
      randomEffects: analysisType === 'lmm' && clusterVariableId
        ? [{
            groupingVariableId: clusterVariableId,
            intercept: true,
            slopeVariableIds: randomEffects[0]?.slopeVariableIds ?? [],
            covariance: randomEffects[0]?.covariance ?? 'correlated',
          }]
        : [],
    })
  }

  const setCentering = (variableId: string, method: 'none' | 'grand_mean' | 'group_mean') => {
    update({
      centering: [
        ...centering.filter(rule => rule.variableId !== variableId),
        { variableId, method },
      ],
    })
  }

  return (
    <div className="adv-multilevel-wizard-panel">
      <h3>{analysisType === 'aggregation' ? 'ICC 与聚合诊断' : '两层 Gaussian LMM'}</h3>
      <p className="muted">
        {analysisType === 'aggregation'
          ? '评估 ICC(1)、ICC(2) 与 rwg 聚合证据；系统不会根据阈值自动替你裁决是否聚合。'
          : '当前支持单一 cluster 的两层 Gaussian LMM。三层、交叉分类与广义结局仍属于后续高级扩展。'}
      </p>
      <p className="muted">当前方法类型由方法库锁定；切换 ICC/LMM 请返回方法库选择另一方法。</p>

      <div className="adv-form-grid adv-form-grid-two">
        <label className="adv-field-label">
          Cluster ID
          <select className="adv-select" value={spec.clusterVariableId} onChange={(event) => updateCluster(event.target.value)}>
            <option value="">请选择团队、班级或机构 ID</option>
            {clusterCandidates.map(variable => <option value={variable.id} key={variable.id}>{variable.label || variable.name}</option>)}
          </select>
        </label>
        {analysisType === 'lmm' ? (
          <label className="adv-field-label">
            最少 cluster 数护栏
            <input
              className="adv-input"
              type="number"
              min={10}
              value={spec.minimumClusterCount ?? 30}
              onChange={event => update({ minimumClusterCount: Math.max(10, Number(event.target.value) || 10) })}
            />
          </label>
        ) : null}
      </div>

      {analysisType === 'lmm' ? (
        <section className="adv-form-section" aria-label="两层线性模型设置">
          <div className="adv-form-grid adv-form-grid-two">
            <label className="adv-field-label">
              结果变量
              <select
                className="adv-select"
                value={spec.outcomeId ?? ''}
                onChange={(event) => {
                  const outcomeId = event.target.value || null
                  update({
                    outcomeId,
                    fixedEffectIds: spec.fixedEffectIds.filter(id => id !== outcomeId),
                    randomEffects: randomEffects.map(effect => ({
                      ...effect,
                      slopeVariableIds: effect.slopeVariableIds.filter(id => id !== outcomeId),
                    })),
                    centering: centering.filter(rule => rule.variableId !== outcomeId),
                  })
                }}
              >
                <option value="">请选择连续结果变量</option>
                {numericVariables.map(variable => <option value={variable.id} key={variable.id}>{variable.label || variable.name}</option>)}
              </select>
            </label>
            <label className="adv-field-label">
              估计方法
              <select className="adv-select" value={spec.estimator} onChange={(event) => update({ estimator: event.target.value as 'REML' | 'ML' })}>
                <option value="REML">REML（方差组分默认）</option>
                <option value="ML">ML（固定效应模型比较）</option>
              </select>
            </label>
            <label className="adv-field-label">
              自由度近似
              <select
                className="adv-select"
                value={spec.degreesOfFreedom ?? 'satterthwaite'}
                onChange={event => update({ degreesOfFreedom: event.target.value as MultilevelWizardSpec['degreesOfFreedom'] })}
              >
                <option value="satterthwaite">Satterthwaite</option>
                <option value="kenward_roger">Kenward–Roger</option>
                <option value="asymptotic">渐近</option>
              </select>
            </label>
          </div>

          <DatasetVariablePicker
            label="固定效应预测变量"
            variables={variables.filter(variable => variable.id !== spec.outcomeId && variable.id !== spec.clusterVariableId)}
            selectedIds={spec.fixedEffectIds}
            onChange={(fixedEffectIds) => update({
              fixedEffectIds,
              centering: centering.filter(rule => fixedEffectIds.includes(rule.variableId)),
              randomEffects: randomEffects.map(effect => ({
                ...effect,
                slopeVariableIds: effect.slopeVariableIds.filter(id => fixedEffectIds.includes(id)),
              })),
            })}
            isMulti
            roleHint="至少选择一个；cluster 随机截距由系统保留"
          />

          {spec.fixedEffectIds.some(id => numericVariables.some(variable => variable.id === id)) ? (
            <fieldset className="adv-form-section">
              <legend>连续预测变量中心化</legend>
              <div className="adv-form-grid adv-form-grid-two">
                {spec.fixedEffectIds
                  .filter(id => numericVariables.some(variable => variable.id === id))
                  .map(variableId => {
                    const variable = numericVariables.find(candidate => candidate.id === variableId)
                    const method = centering.find(rule => rule.variableId === variableId)?.method ?? 'none'
                    return (
                      <label className="adv-field-label" key={variableId}>
                        {variable?.label || variable?.name || variableId}
                        <select className="adv-select" value={method} onChange={event => setCentering(variableId, event.target.value as 'none' | 'grand_mean' | 'group_mean')}>
                          <option value="none">不中心化</option>
                          <option value="grand_mean">总体均值中心化</option>
                          <option value="group_mean">组均值中心化</option>
                        </select>
                      </label>
                    )
                  })}
              </div>
            </fieldset>
          ) : null}

          <DatasetVariablePicker
            label="可选随机斜率"
            variables={numericVariables.filter(variable => spec.fixedEffectIds.includes(variable.id))}
            selectedIds={randomEffects[0]?.slopeVariableIds ?? []}
            onChange={(slopeVariableIds) => update({
              randomEffects: spec.clusterVariableId
                ? [{
                    groupingVariableId: spec.clusterVariableId,
                    intercept: true,
                    slopeVariableIds,
                    covariance: randomEffects[0]?.covariance ?? 'correlated',
                  }]
                : [],
            })}
            isMulti
            roleHint="只从已进入固定效应的连续变量中选择"
          />
        </section>
      ) : (
        <section className="adv-form-section" aria-label="聚合证据设置">
          <DatasetVariablePicker
            label="构成团队层构念的题项"
            variables={scaleCandidates}
            selectedIds={spec.scaleItemIds}
            onChange={(scaleItemIds) => update({ scaleItemIds })}
            isMulti
            roleHint="至少两个题项；rwg 使用下方声明的理论量表范围"
          />
          <div className="adv-form-grid adv-form-grid-three">
            <label className="adv-field-label">理论最小值<input className="adv-input" type="number" value={spec.scaleMin} onChange={(event) => update({ scaleMin: Number(event.target.value) })} /></label>
            <label className="adv-field-label">理论最大值<input className="adv-input" type="number" value={spec.scaleMax} onChange={(event) => update({ scaleMax: Number(event.target.value) })} /></label>
            <label className="adv-field-label">聚合方式<select className="adv-select" value={spec.aggregationMethod} onChange={(event) => update({ aggregationMethod: event.target.value as 'mean' | 'sum' })}><option value="mean">均值</option><option value="sum">总分</option></select></label>
          </div>
        </section>
      )}
    </div>
  )
}
