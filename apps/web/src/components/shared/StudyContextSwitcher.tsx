import { useState } from 'react'
import type {
  DependenceStructure,
  StudyContext,
  StudyDesign,
  TimeStructure,
} from '../../types/study-context'

interface StudyContextSwitcherProps {
  value: StudyContext
  hasDataset: boolean
  persistence?: 'unconfirmed' | 'saving' | 'saved' | 'error'
  onChange: (value: StudyContext) => void
}

const TIME_OPTIONS: Array<{ value: TimeStructure; label: string; description: string }> = [
  { value: 'cross_sectional', label: '单次 / 横截面', description: '每个研究对象在主要时间点记录一次' },
  { value: 'panel', label: '追踪面板', description: '同一对象在有限波次重复测量' },
  { value: 'intensive_longitudinal', label: '密集追踪', description: '日记、ESM / EMA 或高频传感数据' },
]

const DEPENDENCE_OPTIONS: Array<{ value: DependenceStructure; label: string; description: string }> = [
  { value: 'independent', label: '观测相互独立', description: '不存在需要建模的团队、班级或机构依赖' },
  { value: 'nested', label: '存在聚类 / 嵌套', description: '例如员工属于团队、学生属于班级' },
]

const DESIGN_OPTIONS: Array<{ value: StudyDesign; label: string; description: string }> = [
  {
    value: 'observational',
    label: '观察性',
    description: '不随机分配处理，只观察已有差异；如问卷调查、员工自行选择培训。',
  },
  {
    value: 'randomized',
    label: '随机实验',
    description: '随机分配处理组 / 对照组；如随机抽签决定谁接受干预。',
  },
  {
    value: 'quasi_experimental',
    label: '非随机比较',
    description: '保留外部规则或自然分组的上下文；当前不提供准实验因果识别、DiD、IV、RDD 或 IPW。',
  },
]

export function StudyContextSwitcher({ value, hasDataset, onChange, persistence = 'saved' }: StudyContextSwitcherProps) {
  const [editing, setEditing] = useState(false)
  const expanded = !hasDataset || editing || persistence !== 'saved'
  const summary = [
    TIME_OPTIONS.find(option => option.value === value.timeStructure)?.label,
    DEPENDENCE_OPTIONS.find(option => option.value === value.dependenceStructure)?.label,
    DESIGN_OPTIONS.find(option => option.value === value.design)?.label,
  ].join(' · ')
  const update = <Key extends keyof StudyContext>(key: Key, next: StudyContext[Key]) => {
    onChange({ ...value, [key]: next })
  }

  return (
    <section className="study-context-shell" aria-labelledby="study-context-heading">
      <div className="study-context-heading">
        <div>
          <h2 id="study-context-heading">研究结构</h2>
          <p className="study-context-summary">{summary}</p>
          <p role="status">{persistence === 'saved' ? '研究结构已保存' : persistence === 'saving' ? '正在保存研究结构…' : '当前选择尚未保存，请确认研究结构后再分析。'}</p>
        </div>
        {hasDataset ? (
          <button type="button" className="secondary-button" aria-expanded={expanded} aria-controls="study-context-options" onClick={() => setEditing(!editing)}>
            {expanded ? '收起研究结构' : '修改研究结构'}
          </button>
        ) : <span>先选择研究结构，再导入数据</span>}
      </div>

      <div id="study-context-options" hidden={!expanded}>
        {persistence !== 'saved' ? <button type="button" className="secondary-button" disabled={persistence === 'saving'} onClick={() => onChange(value)}>
          {persistence === 'error' ? '重试保存研究结构' : '确认并保存研究结构'}
        </button> : null}
        <p className="study-context-help">{hasDataset ? '修改后需要重新确认数据角色和分析设置；已有结果仍可回看。' : '三个维度分别选择；不确定时，可在导入后修改。'}</p>
      <div className="study-context-groups">
        <fieldset>
          <legend>时间结构</legend>
          {TIME_OPTIONS.map((option) => (
            <label key={option.value} className={value.timeStructure === option.value ? 'is-active' : ''}>
              <input
                type="radio"
                name="time-structure"
                checked={value.timeStructure === option.value}
                onChange={() => update('timeStructure', option.value)}
              />
              <span><strong>{option.label}</strong><small>{option.description}</small></span>
            </label>
          ))}
        </fieldset>

        <fieldset>
          <legend>依赖结构</legend>
          {DEPENDENCE_OPTIONS.map((option) => (
            <label key={option.value} className={value.dependenceStructure === option.value ? 'is-active' : ''}>
              <input
                type="radio"
                name="dependence-structure"
                checked={value.dependenceStructure === option.value}
                onChange={() => update('dependenceStructure', option.value)}
              />
              <span><strong>{option.label}</strong><small>{option.description}</small></span>
            </label>
          ))}
        </fieldset>

        <fieldset className="study-design-options">
          <legend>研究设计</legend>
          {DESIGN_OPTIONS.map((option) => (
            <label key={option.value} className={value.design === option.value ? 'is-active' : ''}>
              <input
                type="radio"
                name="study-design"
                checked={value.design === option.value}
                onChange={() => update('design', option.value)}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </div>
      </div>

      {value.dependenceStructure === 'nested' ? (
        <p className="study-context-notice">
          {value.timeStructure === 'cross_sectional'
            ? '嵌套结构已启用。导入后必须指定 cluster ID，并检查 cluster 数量、组规模、ICC 与聚合依据；普通独立样本回归不会被默认推荐。'
            : '当前选择包含时间内重复测量之外的额外嵌套层级。它通常需要三层或交叉分类模型；当前引导流程会保留该声明并明确提示支持边界。'}
        </p>
      ) : null}
    </section>
  )
}
