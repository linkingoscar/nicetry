import type { DatasetVersion, ModelSpec, ModelVariable } from '../../types'

import { SemStudio } from './SemStudio'

interface ModelEstimationEditorProps {
  model: ModelSpec
  variables: ModelVariable[]
  indicatorCandidates: DatasetVersion['variables']
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void
  onSwitchEstimationFamily: (family: 'ols' | 'sem') => void
}

export function ModelEstimationEditor({
  model,
  variables,
  indicatorCandidates,
  updateModel,
  onSwitchEstimationFamily,
}: ModelEstimationEditorProps) {
  const switchFamily = (family: 'ols' | 'sem') => {
    if (family === model.estimation.family) return
    if (!window.confirm('切换引擎会转换当前节点，并重新初始化测量定义、估计器及多组设置；自定义题项、高阶因子和部分等值约束不会保留。切换后可撤销恢复。是否继续？')) return
    onSwitchEstimationFamily(family)
  }
  return (
    <section className="estimation-editor" aria-labelledby="estimation-editor-heading">
      <div className="section-heading dictionary-heading-row" style={{ gridColumn: '1 / -1' }}>
        <div><p className="eyebrow">Estimation Engine</p><h2 id="estimation-editor-heading">算法引擎与多群组比较</h2></div>
        <div className="template-buttons">
          <button type="button" aria-pressed={model.estimation.family === 'ols'} onClick={() => switchFamily('ols')}>PROCESS (OLS 回归)</button>
          <button type="button" aria-pressed={model.estimation.family === 'sem'} onClick={() => switchFamily('sem')}>lavaan (SEM 结构方程)</button>
        </div>
      </div>

      {model.estimation.family === 'sem' ? (
        <SemStudio
          showMeasurement={false}
          model={model}
          variables={variables}
          indicatorCandidates={indicatorCandidates}
          updateModel={updateModel}
        />
      ) : (
        <>
          <label>
            <span>SE 稳健标准误</span>
            <select
              value={model.estimation.standardErrors}
              onChange={(event) => updateModel((current) => ({
                ...current,
                estimation: {
                  ...current.estimation,
                  standardErrors: event.target.value as 'hc3' | 'bootstrap',
                },
              }))}
            >
              <option value="hc3">HC3 (推荐 - 稳健异方差防护)</option>
              <option value="bootstrap">Bootstrap 5000 次重抽样</option>
            </select>
          </label>

          <label>
            <span>自变量中心化</span>
            <select
              value={model.estimation.centering.method}
              onChange={(event) => updateModel((current) => ({
                ...current,
                estimation: {
                  ...current.estimation,
                  centering: {
                    method: event.target.value as 'none' | 'mean',
                    nodeIds: event.target.value === 'none'
                      ? []
                      : current.nodes
                        .filter((node) => node.dataType === 'continuous' || node.dataType === 'ordinal')
                        .map((node) => node.id),
                  },
                },
              }))}
            >
              <option value="none">原始值 (不中心化)</option>
              <option value="mean">均值中心化 (推荐 - 降低多重共线性)</option>
            </select>
          </label>

          <label>
            <span>缺失值策略</span>
            <select
              value={model.estimation.missing}
              onChange={(event) => updateModel((current) => ({
                ...current,
                estimation: {
                  ...current.estimation,
                  missing: event.target.value as 'complete_cases_per_model' | 'fiml',
                },
              }))}
            >
              <option value="complete_cases_per_model">按方程成对删除 (保留最大样本)</option>
              <option value="fiml">FIML 全信息极大似然 (推荐)</option>
            </select>
          </label>
        </>
      )}
    </section>
  )
}
