interface MethodResultVisualsProps {
  familyResult: Record<string, unknown>
}

type Row = Record<string, unknown>

function rows(value: unknown): Row[] {
  return Array.isArray(value)
    ? value.filter((item): item is Row => Boolean(item) && typeof item === 'object' && !Array.isArray(item))
    : []
}

function firstNumber(row: Row, keys: string[]) {
  for (const key of keys) {
    if (typeof row[key] === 'number' && Number.isFinite(row[key])) return row[key] as number
  }
  return null
}

function firstLabel(row: Row, keys: string[], fallback: string) {
  for (const key of keys) {
    if (typeof row[key] === 'string' || typeof row[key] === 'number') return String(row[key])
  }
  return fallback
}

function MiniLineChart({ data, title, subtitle }: { data: Row[]; title: string; subtitle: string }) {
  const points = data.flatMap((row, index) => {
    const x = firstNumber(row, ['sampleSize', 'n', 'iteration', 'iterationIndex', 'step', 'x']) ?? index + 1
    const y = firstNumber(row, ['power', 'estimate', 'mean', 'value', 'y'])
    const key = String(row.id ?? row.iteration ?? row.sampleSize ?? row.n ?? row.step ?? row.x ?? `${x}:${y}`)
    return y === null ? [] : [{ x, y, key }]
  })
  if (points.length < 2) return null
  const xMin = Math.min(...points.map((point) => point.x))
  const xMax = Math.max(...points.map((point) => point.x))
  const yMin = Math.min(...points.map((point) => point.y))
  const yMax = Math.max(...points.map((point) => point.y))
  const scaleX = (value: number) => 42 + ((value - xMin) / Math.max(xMax - xMin, 1)) * 466
  const scaleY = (value: number) => 174 - ((value - yMin) / Math.max(yMax - yMin, .0001)) * 132
  const polyline = points.map((point) => `${scaleX(point.x)},${scaleY(point.y)}`).join(' ')

  return (
    <figure className="adv-method-figure">
      <figcaption><strong>{title}</strong><span>{subtitle}</span></figcaption>
      <svg viewBox="0 0 540 210" role="img" aria-label={title}>
        <line className="adv-chart-axis" x1="42" y1="174" x2="512" y2="174" />
        <line className="adv-chart-axis" x1="42" y1="34" x2="42" y2="174" />
        <polyline className="adv-chart-line" points={polyline} />
        {points.map((point) => (
          <circle key={point.key} className="adv-chart-point" cx={scaleX(point.x)} cy={scaleY(point.y)} r="3.5" />
        ))}
        <text className="adv-chart-label" x="42" y="195">{xMin.toFixed(0)}</text>
        <text className="adv-chart-label" x="512" y="195" textAnchor="end">{xMax.toFixed(0)}</text>
        <text className="adv-chart-label" x="34" y="39" textAnchor="end">{yMax.toFixed(2)}</text>
        <text className="adv-chart-label" x="34" y="177" textAnchor="end">{yMin.toFixed(2)}</text>
      </svg>
    </figure>
  )
}

function HorizontalEvidencePlot({ data, title, valueKeys }: { data: Row[]; title: string; valueKeys: string[] }) {
  const items = data.flatMap((row, index) => {
    const value = firstNumber(row, valueKeys)
    return value === null ? [] : [{
      label: firstLabel(row, ['itemId', 'item', 'term', 'variable', 'parameter'], `项目 ${index + 1}`),
      value,
    }]
  }).slice(0, 18)
  if (items.length === 0) return null
  const max = Math.max(...items.map((item) => Math.abs(item.value)), 1)
  return (
    <figure className="adv-method-figure">
      <figcaption><strong>{title}</strong><span>图形用于定位异常项目；正式判断仍以估计值、区间和多重检验策略为准。</span></figcaption>
      <div className="adv-evidence-bars">
        {items.map((item) => (
          <div key={item.label}>
            <span title={item.label}>{item.label}</span>
            <i><b style={{ width: `${Math.max(2, Math.abs(item.value) / max * 100)}%` }} /></i>
            <strong>{item.value.toFixed(3)}</strong>
          </div>
        ))}
      </div>
    </figure>
  )
}

function BifactorMetricCards({ value }: { value: unknown }) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const metrics = Object.entries(value)
    .filter(([, result]) => typeof result === 'number')
    .slice(0, 8) as Array<[string, number]>
  if (!metrics.length) return null
  return (
    <section className="adv-method-figure" aria-label="Bifactor 核心诊断">
      <div className="adv-figure-heading"><strong>Bifactor 核心诊断</strong><span>ωh、ECV、PUC 等指标应联合解释，不使用单一固定阈值替代理论判断。</span></div>
      <div className="adv-diagnostic-metrics">
        {metrics.map(([label, result]) => (
          <div key={label}>
            <span>{label}</span>
            <strong>{result.toFixed(3)}</strong>
            <i><b style={{ width: `${Math.min(Math.max(Math.abs(result), 0), 1) * 100}%` }} /></i>
          </div>
        ))}
      </div>
    </section>
  )
}

export function MethodResultVisuals({ familyResult }: MethodResultVisualsProps) {
  if (familyResult.family === 'multiple_imputation') {
    const trace = rows(familyResult.trace ?? familyResult.convergence)
    return <MiniLineChart data={trace} title="MICE 链稳定性" subtitle="检查迭代轨迹是否出现持续漂移；该图不替代链间诊断与插补模型审查。" />
  }
  if (familyResult.family === 'power_analysis') {
    const curve = rows(familyResult.powerCurve ?? familyResult.sensitivityCurve ?? familyResult.simulationResults)
    return <MiniLineChart data={curve} title="功效与样本量敏感性" subtitle="展示当前设计生成的功效变化；Monte Carlo 结果应同时报告 MCSE 与区间。" />
  }
  if (familyResult.family === 'questionnaire_measurement') {
    const irt = familyResult.irt && typeof familyResult.irt === 'object' && !Array.isArray(familyResult.irt)
      ? familyResult.irt as Row
      : null
    const bifactor = familyResult.bifactor && typeof familyResult.bifactor === 'object' && !Array.isArray(familyResult.bifactor)
      ? familyResult.bifactor as Row
      : null
    return (
      <div className="adv-method-visual-grid">
        <BifactorMetricCards value={bifactor?.bifactorMetrics} />
        <HorizontalEvidencePlot data={rows(irt?.itemParameters)} title="IRT 区分度概览" valueKeys={['discrimination', 'a', 'estimate']} />
        <HorizontalEvidencePlot data={rows(irt?.difAnalysis)} title="DIF 效应筛查" valueKeys={['effectSize', 'deltaR2', 'statistic', 'estimate']} />
      </div>
    )
  }
  return null
}
