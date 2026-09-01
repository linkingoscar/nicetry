import { useState, type DragEvent, type ReactNode } from 'react'
import type { AdvancedAnalysisSpec, MultilevelModelSpec } from '../../types'
import './visual-builder.css'

interface VisualFormulaBuilderProps {
  spec: AdvancedAnalysisSpec
  onChange: (spec: AdvancedAnalysisSpec) => void
}

type BuilderZone = 'pool' | 'outcome' | 'fixed' | 'intercept' | 'slopes'

interface SelectedVariable {
  source: BuilderZone
  variableId: string
}

type RandomEffect = NonNullable<MultilevelModelSpec['randomEffects']>[number]

const DEFAULT_RANDOM_EFFECT: RandomEffect = {
  groupingVariableId: '',
  intercept: true,
  slopeVariableIds: [],
  covariance: 'correlated',
}

const ZONE_LABELS: Record<Exclude<BuilderZone, 'pool'>, string> = {
  outcome: '因变量区',
  fixed: '固定效应区',
  intercept: '随机截距区',
  slopes: '随机斜率区',
}

function isBuilderZone(value: unknown): value is BuilderZone {
  return value === 'pool' || value === 'outcome' || value === 'fixed' || value === 'intercept' || value === 'slopes'
}

function parseDraggedVariable(value: string): SelectedVariable | null {
  try {
    const parsed: unknown = JSON.parse(value)
    if (
      typeof parsed === 'object' &&
      parsed !== null &&
      'variableId' in parsed &&
      'source' in parsed &&
      typeof parsed.variableId === 'string' &&
      isBuilderZone(parsed.source)
    ) {
      return { variableId: parsed.variableId, source: parsed.source }
    }
  } catch {
    return null
  }

  return null
}

function addUnique(values: string[], value: string): string[] {
  return values.includes(value) ? values : [...values, value]
}

export function VisualFormulaBuilder({ spec, onChange }: VisualFormulaBuilderProps) {
  const [availableVars, setAvailableVars] = useState<string[]>([
    'Score',
    'Age',
    'Gender',
    'Treatment',
    'SchoolID',
    'ClassID',
    'Time',
  ])
  const [newVar, setNewVar] = useState('')
  const [selectedVariable, setSelectedVariable] = useState<SelectedVariable | null>(null)

  if (spec.family !== 'multilevel_model') {
    return (
      <div className="vfb-unsupported">
        <p>可视化公式构建器目前仅支持多层线性模型 (MLM)。</p>
      </div>
    )
  }

  const outcome = spec.outcomeId
  const fixedEffects = spec.fixedEffectIds ?? []
  const randomEffects = spec.randomEffects ?? []
  const randomEffect = randomEffects[0] ?? DEFAULT_RANDOM_EFFECT
  const randomIntercept = randomEffect.groupingVariableId || spec.clusterVariableId
  const randomSlopes = randomEffect.slopeVariableIds ?? []

  const moveVariable = (variableId: string, source: BuilderZone, target: BuilderZone) => {
    if (source === target) return

    let nextOutcome = spec.outcomeId
    let nextFixedEffects = [...fixedEffects]
    let nextClusterVariableId = spec.clusterVariableId
    let nextRandomEffect = randomEffect
    let randomEffectChanged = false

    const updateRandomEffect = (changes: Partial<RandomEffect>) => {
      nextRandomEffect = { ...nextRandomEffect, ...changes }
      randomEffectChanged = true
    }

    switch (source) {
      case 'outcome':
        nextOutcome = ''
        break
      case 'fixed':
        nextFixedEffects = nextFixedEffects.filter(value => value !== variableId)
        break
      case 'intercept':
        nextClusterVariableId = ''
        updateRandomEffect({ groupingVariableId: '' })
        break
      case 'slopes':
        updateRandomEffect({
          slopeVariableIds: randomSlopes.filter(value => value !== variableId),
        })
        break
      case 'pool':
        break
    }

    switch (target) {
      case 'outcome':
        nextOutcome = variableId
        break
      case 'fixed':
        nextFixedEffects = addUnique(nextFixedEffects, variableId)
        break
      case 'intercept':
        nextClusterVariableId = variableId
        updateRandomEffect({ groupingVariableId: variableId, intercept: true })
        break
      case 'slopes':
        updateRandomEffect({
          slopeVariableIds: addUnique(nextRandomEffect.slopeVariableIds ?? [], variableId),
        })
        break
      case 'pool':
        break
    }

    onChange({
      ...spec,
      outcomeId: nextOutcome,
      fixedEffectIds: nextFixedEffects,
      clusterVariableId: nextClusterVariableId,
      randomEffects: randomEffectChanged
        ? [nextRandomEffect, ...randomEffects.slice(1)]
        : randomEffects,
    })
    setSelectedVariable(null)
  }

  const handleDragStart = (event: DragEvent<HTMLButtonElement>, variableId: string, source: BuilderZone) => {
    const payload = JSON.stringify({ variableId, source })
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('application/x-researchpath-variable', payload)
    event.dataTransfer.setData('text/plain', payload)
  }

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const zoneElement = (event.target as HTMLElement).closest<HTMLElement>('[data-drop-zone]')
    const target = zoneElement?.dataset.dropZone
    if (!isBuilderZone(target)) return

    const dragged =
      parseDraggedVariable(event.dataTransfer.getData('application/x-researchpath-variable')) ??
      parseDraggedVariable(event.dataTransfer.getData('text/plain'))
    if (dragged) moveVariable(dragged.variableId, dragged.source, target)
  }

  const addVariable = () => {
    const variableId = newVar.trim()
    if (!variableId) return
    if (!availableVars.includes(variableId)) {
      setAvailableVars(current => [...current, variableId])
    }
    setNewVar('')
  }

  const renderChip = (variableId: string, source: Exclude<BuilderZone, 'pool'>) => (
    <div key={variableId} className="vfb-chip-actions">
      <button
        type="button"
        className="vfb-var-chip active"
        draggable
        onDragStart={event => handleDragStart(event, variableId, source)}
        onClick={() => setSelectedVariable({ variableId, source })}
        aria-pressed={selectedVariable?.variableId === variableId && selectedVariable.source === source}
      >
        {variableId}
      </button>
      <button
        type="button"
        className="vfb-remove"
        onClick={() => moveVariable(variableId, source, 'pool')}
        aria-label={`从${ZONE_LABELS[source]}移除 ${variableId}`}
      >
        ×
      </button>
    </div>
  )

  const renderZone = (
    zone: Exclude<BuilderZone, 'pool'>,
    title: string,
    content: ReactNode,
    placeholder: string,
    multi = false,
  ) => (
    <div className="vfb-zone" data-drop-zone={zone}>
      <div className="vfb-zone-heading">
        <h4 className="vfb-title">{title}</h4>
        <button
          type="button"
          className="vfb-assign-button"
          onClick={() => selectedVariable && moveVariable(selectedVariable.variableId, selectedVariable.source, zone)}
          disabled={!selectedVariable}
        >
          放入此处
        </button>
      </div>
      <div className={`vfb-drop-area${multi ? ' multi' : ''}`}>
        {content ?? <span className="vfb-placeholder">{placeholder}</span>}
      </div>
    </div>
  )

  return (
    <div
      className="vfb-container"
      role="application"
      aria-label="多层模型可视化公式构建器"
      aria-describedby="vfb-instructions"
      onDragOver={event => event.preventDefault()}
      onDrop={handleDrop}
    >
      <p id="vfb-instructions" className="vfb-instructions">
        可拖拽变量到目标区域；键盘操作时，先选择变量，再点击目标区域的“放入此处”。
      </p>
      <div className="vfb-sidebar" data-drop-zone="pool">
        <h4 className="vfb-title">可用变量</h4>
        <div className="vfb-add-var">
          <input
            type="text"
            placeholder="输入新变量名..."
            value={newVar}
            onChange={event => setNewVar(event.target.value)}
            onKeyDown={event => {
              if (event.key === 'Enter') addVariable()
            }}
          />
          <button type="button" onClick={addVariable} aria-label="添加变量">
            +
          </button>
        </div>
        <div className="vfb-vars-list">
          {availableVars.map(variableId => (
            <button
              key={variableId}
              type="button"
              className="vfb-var-chip"
              draggable
              onDragStart={event => handleDragStart(event, variableId, 'pool')}
              onClick={() => setSelectedVariable({ variableId, source: 'pool' })}
              aria-pressed={selectedVariable?.variableId === variableId && selectedVariable.source === 'pool'}
            >
              {variableId}
            </button>
          ))}
        </div>
      </div>

      <div className="vfb-builder-area">
        {selectedVariable && (
          <p className="vfb-selection-status" role="status">
            已选择 {selectedVariable.variableId}；请选择目标区域。
          </p>
        )}
        <div className="vfb-zone-row">
          {renderZone('outcome', '因变量 (Outcome)', outcome ? renderChip(outcome, 'outcome') : null, '拖入变量')}
        </div>
        <div className="vfb-zone-row">
          {renderZone(
            'fixed',
            '固定效应区 (Fixed Effects)',
            fixedEffects.length > 0 ? fixedEffects.map(variableId => renderChip(variableId, 'fixed')) : null,
            '拖入预测变量',
            true,
          )}
        </div>
        <div className="vfb-zone-row split">
          {renderZone(
            'intercept',
            '随机截距区 (聚类变量)',
            randomIntercept ? renderChip(randomIntercept, 'intercept') : null,
            '拖入聚类 ID (如 SchoolID)',
          )}
          {renderZone(
            'slopes',
            '随机斜率区 (Random Slopes)',
            randomSlopes.length > 0 ? randomSlopes.map(variableId => renderChip(variableId, 'slopes')) : null,
            '拖入需随群组变化的变量',
            true,
          )}
        </div>
      </div>
    </div>
  )
}
