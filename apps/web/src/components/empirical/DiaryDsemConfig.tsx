import type { DiaryDsemOptions } from '../../types'

interface DiaryDsemConfigProps {
  dsem: DiaryDsemOptions
  onChange: (patch: { dsem: DiaryDsemOptions }) => void
}

export function DiaryDsemConfig({ dsem, onChange }: DiaryDsemConfigProps) {
  return (
    <fieldset className="analysis-config-subsection">
      <legend>Bayesian DSEM 抽样与先验</legend>
      <div className="empirical-config-grid">
        <label>链数
          <input
            type="number"
            min="2"
            max="8"
            value={dsem.chains}
            onChange={(event) => onChange({
              dsem: { ...dsem, chains: Number(event.target.value) },
            })}
          />
        </label>
        <label>每链迭代
          <input
            type="number"
            min="400"
            max="20000"
            step="100"
            value={dsem.iterations}
            onChange={(event) => onChange({
              dsem: { ...dsem, iterations: Number(event.target.value) },
            })}
          />
        </label>
        <label>Warmup
          <input
            type="number"
            min="200"
            max="10000"
            step="100"
            value={dsem.warmup}
            onChange={(event) => onChange({
              dsem: { ...dsem, warmup: Number(event.target.value) },
            })}
          />
        </label>
        <label>抽稀间隔
          <input
            type="number"
            min="1"
            max="20"
            value={dsem.thin}
            onChange={(event) => onChange({
              dsem: { ...dsem, thin: Number(event.target.value) },
            })}
          />
        </label>
        <label>固定效应先验 SD
          <input
            type="number"
            min="0.01"
            max="10"
            step="0.1"
            value={dsem.priorMeanSd}
            onChange={(event) => onChange({
              dsem: { ...dsem, priorMeanSd: Number(event.target.value) },
            })}
          />
        </label>
        <label>方差先验尺度
          <input
            type="number"
            min="0.01"
            max="10"
            step="0.1"
            value={dsem.priorScale}
            onChange={(event) => onChange({
              dsem: { ...dsem, priorScale: Number(event.target.value) },
            })}
          />
        </label>
        <label>每链绘图抽样
          <input
            type="number"
            min="100"
            max="500"
            step="50"
            value={dsem.plotDrawsPerChain}
            onChange={(event) => onChange({
              dsem: { ...dsem, plotDrawsPerChain: Number(event.target.value) },
            })}
          />
        </label>
        <label>预测检验重复数
          <input
            type="number"
            min="100"
            max="500"
            step="50"
            value={dsem.predictiveReplications}
            onChange={(event) => onChange({
              dsem: { ...dsem, predictiveReplications: Number(event.target.value) },
            })}
          />
        </label>
      </div>
      <label className="analysis-inline-checkbox">
        <input
          type="checkbox"
          checked={dsem.randomDynamicSlopes}
          onChange={(event) => onChange({
            dsem: { ...dsem, randomDynamicSlopes: event.target.checked },
          })}
        />
        允许自回归与交叉滞后系数在被试间随机变化
      </label>
      <label className="analysis-inline-checkbox">
        <input
          type="checkbox"
          checked={dsem.runPriorSensitivity}
          onChange={(event) => onChange({
            dsem: { ...dsem, runPriorSensitivity: event.target.checked },
          })}
        />
        对固定效应先验执行 0.5×/2×重要性重加权敏感性分析
      </label>
      <p className="analysis-note">
        至少要求每人 20 个有效时点。平台运行观测变量双向 Bayesian 多层 VAR(1)
        切片并报告 rank-normalized R-hat、bulk/tail ESS、MCSE、预测检验与平稳性；
        不冒充 Mplus 潜变量 DSEM。
      </p>
    </fieldset>
  )
}
