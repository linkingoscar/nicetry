import { useState, type FC } from 'react'
import { templateLabels, type ModelTemplate } from './modelTemplates'
import { ProcessPresetPicker } from './ProcessPresetPicker'

interface ModelBuilderToolbarProps {
  template: ModelTemplate
  isCustom?: boolean
  draftState: 'saving' | 'saved' | 'error'
  zenMode?: boolean
  leftCollapsed?: boolean
  rightCollapsed?: boolean
  canUndo?: boolean
  canRedo?: boolean
  onUndo?: () => void
  onRedo?: () => void
  onSelectTemplate: (template: ModelTemplate, count?: number) => void
  onCreateCustom: () => void
  onToggleZenMode?: () => void
  onToggleLeft?: () => void
  onToggleRight?: () => void
  onResetLayout?: () => void
  editingDisabled?: boolean
}

const TEMPLATE_GROUPS: Array<{
  id: string
  label: string
  question: string
  templates: ModelTemplate[]
}> = [
  { id: 'moderation', label: '调节效应', question: '关系是否随第三个变量而改变？', templates: ['model_1', 'model_2', 'model_3'] },
  { id: 'mediation', label: '中介分析', question: '变量之间的间接关联如何分解？', templates: ['model_4', 'model_6'] },
  { id: 'conditional', label: '有调节的中介', question: '机制在什么条件下更强或更弱？', templates: ['model_5', 'model_7', 'model_8', 'model_14', 'model_15'] },
  { id: 'complex', label: '复杂条件过程', question: '多个阶段或边界条件如何共同作用？', templates: ['model_21', 'model_22', 'model_58', 'model_59'] },
]

export const ModelBuilderToolbar: FC<ModelBuilderToolbarProps> = ({
  template,
  isCustom = false,
  draftState,
  zenMode = false,
  leftCollapsed = false,
  rightCollapsed = false,
  canUndo = false,
  canRedo = false,
  onUndo,
  onRedo,
  onSelectTemplate,
  onCreateCustom,
  onToggleZenMode,
  onToggleLeft,
  onToggleRight,
  onResetLayout,
  editingDisabled = false,
}) => {
  const initialGroup = TEMPLATE_GROUPS.find((group) => group.templates.includes(template))?.id ?? TEMPLATE_GROUPS[0].id
  const [activeGroupId, setActiveGroupId] = useState(initialGroup)
  const activeGroup = TEMPLATE_GROUPS.find((group) => group.id === activeGroupId) ?? TEMPLATE_GROUPS[0]
  return (
    <section className="model-toolbar" aria-labelledby="builder-heading">
      <div>
        <p className="eyebrow">理论模型设计</p>
        <h1 id="builder-heading">模型画布与预运行检查</h1>
        <p className="muted">选模型 → 分配变量 → 设置路径 → 检查并运行。每次只估计当前模型。</p>
        <ul className="catalog-coverage" aria-label="PROCESS 5.0 模型覆盖范围">
          <li>55 个编号可识别，执行以检查为准</li>
          <li>55 个预设均可预览和选用</li>
          <li>自定义结构可保存</li>
        </ul>
      </div>
      <div className="process-toolbar-actions">
        <div className="view-controls">
          {onUndo ? (
            <button
              type="button"
              className="view-toggle-btn"
              disabled={!canUndo || editingDisabled}
              onClick={onUndo}
              title="撤销画布操作 (Ctrl+Z)"
            >
              ↩ 撤销
            </button>
          ) : null}
          {onRedo ? (
            <button
              type="button"
              className="view-toggle-btn"
              disabled={!canRedo || editingDisabled}
              onClick={onRedo}
              title="重做画布操作 (Ctrl+Y)"
            >
              ↪ 重做
            </button>
          ) : null}
          {onResetLayout ? (
            <button
              type="button"
              className="view-toggle-btn"
              onClick={onResetLayout}
              disabled={editingDisabled}
              title="复位节点位置至模板默认排版"
            >
              重置排版
            </button>
          ) : null}
          <span className="toolbar-divider" aria-hidden="true" />
          {onToggleLeft ? (
            <button
              type="button"
              className={`view-toggle-btn ${leftCollapsed ? 'is-active' : ''}`}
              onClick={onToggleLeft}
              aria-expanded={!leftCollapsed && !zenMode}
              title="折叠/展开左侧变量库"
            >
              {leftCollapsed ? '▶ 变量库' : '◀ 变量库'}
            </button>
          ) : null}
          {onToggleRight ? (
            <button
              type="button"
              className={`view-toggle-btn ${rightCollapsed ? 'is-active' : ''}`}
              onClick={onToggleRight}
              aria-expanded={!rightCollapsed && !zenMode}
              title="折叠/展开右侧检查栏"
            >
              {rightCollapsed ? '检查栏 ◀' : '检查栏 ▶'}
            </button>
          ) : null}
          {onToggleZenMode ? (
            <button
              type="button"
              className={`view-toggle-btn ${zenMode ? 'is-active' : ''}`}
              onClick={onToggleZenMode}
              aria-pressed={zenMode}
              title="禅模式 (Ctrl+Shift+Z)"
            >
              {zenMode ? '退出专注模式' : '专注模式'}
            </button>
          ) : null}
        </div>
        <div className="draft-indicator" data-state={draftState}>
          {draftState === 'saving' ? '草稿保存中…' : draftState === 'saved' ? '草稿已保存' : '草稿保存失败'}
        </div>
      </div>
      <details className="template-explorer">
        <summary>更换模型 · {isCustom ? '自定义结构' : templateLabels[template]}</summary>
        <div className="template-explorer-title-row">
          <strong className="template-explorer-title">{isCustom ? '自定义结构构建' : '常用模型快速起步'}</strong>
          <button
            type="button"
            className={`custom-model-button${isCustom ? ' is-active' : ''}`}
            aria-pressed={isCustom}
            onClick={onCreateCustom}
            disabled={editingDisabled}
          >
            自定义构建
          </button>
        </div>
        <fieldset className="template-group-tabs" aria-label="按研究问题选择模型类型">
          {TEMPLATE_GROUPS.map((group) => (
            <button
              type="button"
              key={group.id}
              aria-pressed={activeGroup.id === group.id}
              onClick={() => setActiveGroupId(group.id)}
            >
              <strong>{group.label}</strong>
              <small>{group.question}</small>
            </button>
          ))}
        </fieldset>
        <fieldset className="template-buttons">
          <legend>{activeGroup.question}</legend>
          {activeGroup.templates.map((key) => (
            <button
              type="button"
              key={key}
              aria-pressed={template === key && !isCustom}
              onClick={() => onSelectTemplate(key)}
              disabled={editingDisabled}
            >
              {templateLabels[key]}
            </button>
          ))}
        </fieldset>
        <ProcessPresetPicker onSelect={onSelectTemplate} disabled={editingDisabled} />
      </details>
    </section>
  )
}
