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
  estimator: 'REML' | 'ML'
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
}

export function MultilevelWizard({ spec, onChange, variables }: MultilevelWizardProps) {
  const update = (patch: Partial<MultilevelWizardSpec>) => onChange({ ...spec, ...patch })
  // Cluster identifiers are frequently stored as numeric codes (e.g. 1..K),
  // so the data type alone must not exclude a role already confirmed by the
  // structure profile. Date/time columns are the only clearly unsafe default.
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
      randomEffects: spec.analysisType === 'lmm' && clusterVariableId
        ? [{
            groupingVariableId: clusterVariableId,
            intercept: true,
            slopeVariableIds: spec.randomEffects[0]?.slopeVariableIds ?? [],
            covariance: 'correlated',
          }]
        : [],
    })
  }

  return (
    <div className="adv-multilevel-wizard-panel">
      <h3>横截面聚类与两层模型</h3>
      <p className="muted">当前实验性边界：单一 cluster 的两层 Gaussian LMM，或 ICC(1)/ICC(2)/rwg 聚合证据。三层、交叉分类与广义结局暂不开放。</p>

      <div className="adv-form-grid adv-form-grid-two">
        <label className="adv-field-label">
          分析目标
          <select
            className="adv-select"
            value={spec.analysisType}
            onChange={(event) => update({
              analysisType: event.target.value as MultilevelWizardSpec['analysisType'],
              randomEffects: event.target.value === 'lmm' && spec.clusterVariableId
                ? [{ groupingVariableId: spec.clusterVariableId, intercept: true, slopeVariableIds: [], covariance: 'correlated' }]
                : [],
            })}
          >
            <option value="lmm">解释个体结果：两层 Gaussian LMM</option>
            <option value="aggregation">聚合证据：ICC 与 rwg（不自动裁决）</option>
          </select>
        </label>
        <label className="adv-field-label">
          Cluster ID
          <select className="adv-select" value={spec.clusterVariableId} onChange={(event) => updateCluster(event.target.value)}>
            <option value="">请选择团队、班级或机构 ID</option>
            {clusterCandidates.map(variable => <option value={variable.id} key={variable.id}>{variable.label || variable.name}</option>)}
          </select>
        </label>
      </div>

      {spec.analysisType === 'lmm' ? (
        <section className="adv-form-section" aria-label="两层线性模型规格">
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
                    randomEffects: spec.randomEffects.map(effect => ({
                      ...effect,
                      slopeVariableIds: effect.slopeVariableIds.filter(id => id !== outcomeId),
                    })),
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
                <option value="REML">REML</option>
                <option value="ML">ML</option>
              </select>
            </label>
          </div>
          <DatasetVariablePicker
            label="固定效应预测变量"
            variables={variables.filter(variable => variable.id !== spec.outcomeId && variable.id !== spec.clusterVariableId)}
            selectedIds={spec.fixedEffectIds}
            onChange={(fixedEffectIds) => update({ fixedEffectIds })}
            isMulti
            roleHint="至少选择一个；系统默认加入 cluster 随机截距"
          />
          <DatasetVariablePicker
            label="可选随机斜率"
            variables={numericVariables.filter(variable => spec.fixedEffectIds.includes(variable.id))}
            selectedIds={spec.randomEffects[0]?.slopeVariableIds ?? []}
            onChange={(slopeVariableIds) => update({
              randomEffects: spec.clusterVariableId
                ? [{ groupingVariableId: spec.clusterVariableId, intercept: true, slopeVariableIds, covariance: 'correlated' }]
                : [],
            })}
            isMulti
            roleHint="只从已进入固定效应的连续变量中选择"
          />
        </section>
      ) : (
        <section className="adv-form-section" aria-label="聚合证据规格">
          <DatasetVariablePicker
            label="构成团队层构念的题项"
            variables={scaleCandidates}
            selectedIds={spec.scaleItemIds}
            onChange={(scaleItemIds) => update({ scaleItemIds })}
            isMulti
            roleHint="至少两个题项；rwg 将使用下方声明的理论量表范围"
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
