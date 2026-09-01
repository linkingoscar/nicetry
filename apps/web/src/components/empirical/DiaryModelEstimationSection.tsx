import type { DiaryMultilevelOptions } from '../../types'
import { DiaryPowerConfig } from './PowerAnalysisConfig'

interface DiaryModelEstimationSectionProps {
  value: DiaryMultilevelOptions
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryModelEstimationSection({
  value,
  onChange,
}: DiaryModelEstimationSectionProps) {
  return (
    <>
      <fieldset className="analysis-config-subsection">
        <legend>模型变量缺失处理</legend>
        <div className="empirical-config-grid">
          <label>缺失策略
            <select
              value={value.missingStrategy}
              onChange={(event) => onChange({
                missingStrategy: event.target.value as DiaryMultilevelOptions['missingStrategy'],
              })}
            >
              <option value="complete_cases">模型完整案例</option>
              {value.analysisType === 'lmm' ? (
                <option value="multilevel_mi">二层多重插补</option>
              ) : null}
            </select>
          </label>
          {value.missingStrategy === 'multilevel_mi' ? (
            <>
              <label>插补数据集数
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={value.imputationCount}
                  onChange={(event) => onChange({ imputationCount: Number(event.target.value) })}
                />
              </label>
              <label>每次迭代数
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={value.imputationIterations}
                  onChange={(event) => onChange({
                    imputationIterations: Number(event.target.value),
                  })}
                />
              </label>
            </>
          ) : null}
        </div>
        <p className="method-note">
          二层插补保留被试聚类，连续时变变量使用 2l.pan，被试层变量使用 2lonly.pmm，并按 Rubin 规则合并固定效应。
        </p>
      </fieldset>
      {value.analysisType === 'lmm' ? (
        <DiaryPowerConfig
          value={value.powerAnalysis}
          onChange={(powerAnalysis) => onChange({ powerAnalysis })}
        />
      ) : null}
      {value.analysisType !== 'bayesian_dsem' ? <label className="analysis-inline-checkbox">
        <input
          type="checkbox"
          checked={value.runRobustnessChecks}
          onChange={(event) => onChange({ runRobustnessChecks: event.target.checked })}
        />
        自动比较随机效应与残差结构稳健性
      </label> : null}
    </>
  )
}
