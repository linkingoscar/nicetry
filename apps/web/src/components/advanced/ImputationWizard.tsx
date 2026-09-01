import { DatasetVariablePicker, type DatasetVariableItem } from './DatasetVariablePicker'

type ImputationMethod = 'auto' | 'pmm' | 'normal' | 'logistic' | 'multinomial_logistic' | 'ordinal_logistic' | 'cart' | 'two_level_normal' | 'two_level_binary'

interface ImputationVariableSpec {
  variableId: string
  method: ImputationMethod
  predictorIds: string[]
}

interface PooledAnalysisSpec {
  modelType: 'linear_regression'
  outcomeId: string
  predictorIds: string[]
  includeIntercept: boolean
}

export interface ImputationWizardSpec {
  family: 'multiple_imputation'
  datasetVersionId?: string
  method: 'mice_fcs'
  imputations: number
  iterations: number
  variables: ImputationVariableSpec[]
  passiveRules?: Array<{ targetVariableId: string; expression: string }>
  clusterVariableId?: string | null
  pooling: 'rubin'
  pooledAnalysis: PooledAnalysisSpec
  substantiveModelHash?: string
  diagnostics: Array<'trace' | 'distribution' | 'overimputation' | 'fraction_missing_information'>
  seed?: number
}

export interface ImputationWizardProps {
  spec: ImputationWizardSpec
  onChange: (spec: ImputationWizardSpec) => void
  variables: DatasetVariableItem[]
}

function analysisVariableIds(spec: ImputationWizardSpec): string[] {
  return Array.from(new Set([
    spec.pooledAnalysis.outcomeId,
    ...spec.pooledAnalysis.predictorIds,
  ].filter(Boolean)))
}

function synchronizePredictors(
  variables: ImputationVariableSpec[],
  modelVariableIds: string[],
): ImputationVariableSpec[] {
  return variables.map(variable => ({
    ...variable,
    predictorIds: Array.from(new Set([
      ...variable.predictorIds,
      ...modelVariableIds.filter(id => id !== variable.variableId),
    ])),
  }))
}

function defaultMethod(variable?: DatasetVariableItem): ImputationMethod {
  if (variable?.type !== 'categorical') return 'pmm'
  return variable.levels === 2 ? 'logistic' : 'multinomial_logistic'
}

export function ImputationWizard({ spec, onChange, variables }: ImputationWizardProps) {
  const update = (patch: Partial<ImputationWizardSpec>) => onChange({ ...spec, ...patch })
  const selectedVariableIds = spec.variables.map(variable => variable.variableId)
  const modelVariableIds = analysisVariableIds(spec)
  const outcomeCandidates = variables.filter(variable => variable.type === 'numeric')

  const updateAnalysisModel = (pooledAnalysis: PooledAnalysisSpec) => {
    const nextModelIds = Array.from(new Set([
      pooledAnalysis.outcomeId,
      ...pooledAnalysis.predictorIds,
    ].filter(Boolean)))
    update({
      pooledAnalysis,
      substantiveModelHash: undefined,
      variables: synchronizePredictors(spec.variables, nextModelIds),
    })
  }

  const handleSelectionChange = (ids: string[]) => {
    const updated = ids.map(variableId => {
      const existing = spec.variables.find(variable => variable.variableId === variableId)
      if (existing) return existing
      return {
        variableId,
        method: defaultMethod(variables.find(variable => variable.id === variableId)),
        predictorIds: modelVariableIds.filter(id => id !== variableId),
      }
    })
    update({ variables: synchronizePredictors(updated, modelVariableIds) })
  }

  return (
    <div className="adv-imputation-wizard-panel">
      <h3>与核心分析绑定的多重插补</h3>
      <p className="muted">
        先冻结下游线性分析的结果变量与预测变量，再配置 MICE。系统会把全部核心分析变量加入每个插补模型；当前只开放 Rubin 合并的线性回归切片。
      </p>
      {spec.substantiveModelHash ? (
        <p className="method-note"><strong>核心模型指纹：</strong><code>{spec.substantiveModelHash}</code>。修改 Y 或预测变量后必须重新验证并重新生成插补。</p>
      ) : null}

      <section className="adv-form-section" aria-labelledby="mi-analysis-model-heading">
        <h4 id="mi-analysis-model-heading">1. 声明下游核心分析模型</h4>
        <div className="adv-form-grid">
          <label>
            结果变量 Y
            <select
              className="adv-select"
              value={spec.pooledAnalysis.outcomeId}
              onChange={(event) => updateAnalysisModel({
                ...spec.pooledAnalysis,
                outcomeId: event.target.value,
                predictorIds: spec.pooledAnalysis.predictorIds.filter(id => id !== event.target.value),
              })}
            >
              <option value="">请选择结果变量</option>
              {outcomeCandidates.map(variable => <option value={variable.id} key={variable.id}>{variable.label || variable.name}</option>)}
            </select>
          </label>
        </div>
        <DatasetVariablePicker
          label="核心预测变量与协变量"
          variables={variables.filter(variable => variable.id !== spec.pooledAnalysis.outcomeId)}
          selectedIds={spec.pooledAnalysis.predictorIds}
          onChange={(predictorIds) => updateAnalysisModel({ ...spec.pooledAnalysis, predictorIds })}
          isMulti
          roleHint="至少选择一个；交互或非线性模型目前不在本切片支持范围"
        />
      </section>

      <section className="adv-form-section" aria-labelledby="mi-variables-heading">
        <h4 id="mi-variables-heading">2. 选择需要插补的变量</h4>
        <DatasetVariablePicker
          label="存在缺失的分析变量"
          variables={variables}
          selectedIds={selectedVariableIds}
          onChange={handleSelectionChange}
          isMulti
          roleHint="正式运行前，每个插补模型都会包含上方声明的 Y、预测变量与协变量"
        />
        {spec.variables.length > 0 ? (
          <table className="adv-table">
            <thead><tr><th>变量</th><th>插补方法</th><th>强制纳入的分析变量</th></tr></thead>
            <tbody>
              {spec.variables.map((item, index) => {
                const metadata = variables.find(variable => variable.id === item.variableId)
                return (
                  <tr key={item.variableId}>
                    <td>{metadata?.label || metadata?.name || item.variableId}</td>
                    <td>
                      <select
                        className="adv-select"
                        value={item.method}
                        onChange={(event) => {
                          const next = [...spec.variables]
                          next[index] = { ...item, method: event.target.value as ImputationMethod }
                          update({ variables: next })
                        }}
                      >
                        <option value="auto">自动</option>
                        <option value="pmm">PMM（连续）</option>
                        <option value="normal">Normal（连续）</option>
                        <option value="logistic">Logistic（二元）</option>
                        <option value="multinomial_logistic">多项 Logistic</option>
                        <option value="ordinal_logistic">有序 Logistic</option>
                        <option value="cart">CART</option>
                      </select>
                    </td>
                    <td>{item.predictorIds.join('、') || '待选择核心分析变量'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        ) : null}
      </section>

      <section className="adv-form-section" aria-labelledby="mi-run-heading">
        <h4 id="mi-run-heading">3. 插补与合并设置</h4>
        <div className="adv-form-grid">
          <label>插补数据集数量<input className="adv-input" type="number" min={5} max={200} value={spec.imputations} onChange={(event) => update({ imputations: Number(event.target.value) || 20 })} /></label>
          <label>每条链迭代轮次<input className="adv-input" type="number" min={5} max={100} value={spec.iterations} onChange={(event) => update({ iterations: Number(event.target.value) || 20 })} /></label>
          <label>合并策略<input className="adv-input" value="Rubin pooling（线性回归）" readOnly /></label>
        </div>
      </section>
    </div>
  )
}
