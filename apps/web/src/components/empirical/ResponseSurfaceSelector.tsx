interface ResponseSurfaceSelectorProps {
  scores: Array<{ id: string; label: string }>
  outcomeVariableId: string | null
  value: string[]
  onChange: (value: string[]) => void
}

export function ResponseSurfaceSelector({
  scores,
  outcomeVariableId,
  value,
  onChange,
}: ResponseSurfaceSelectorProps) {
  const candidates = scores.filter((score) => score.id !== outcomeVariableId)
  const update = (index: number, next: string) => {
    if (!next) {
      onChange([])
      return
    }
    const updated = [...value]
    updated[index] = next
    onChange(updated.length === 2 && updated[0] !== updated[1] ? updated : updated.slice(0, 1))
  }
  return (
    <fieldset className="analysis-variable-picker response-surface-picker">
      <legend>可选：多项式回归与响应面</legend>
      <label>焦点变量 X
        <select value={value[0] ?? ''} onChange={(event) => update(0, event.target.value)}>
          <option value="">不运行响应面</option>
          {candidates.filter((score) => score.id !== value[1]).map((score) => (
            <option key={score.id} value={score.id}>{score.label}</option>
          ))}
        </select>
      </label>
      <label>焦点变量 Z
        <select
          value={value[1] ?? ''}
          disabled={!value[0]}
          onChange={(event) => update(1, event.target.value)}
        >
          <option value="">请选择第二个变量</option>
          {candidates.filter((score) => score.id !== value[0]).map((score) => (
            <option key={score.id} value={score.id}>{score.label}</option>
          ))}
        </select>
      </label>
      <span className="muted response-surface-help">按选择顺序解释 X 与 Z；模型包含 X、Z、X²、X×Z、Z²。</span>
    </fieldset>
  )
}
