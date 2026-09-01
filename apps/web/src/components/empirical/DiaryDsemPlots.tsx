import type { DiaryDsemPlotParameter } from '../../types'

interface DiaryDsemPlotsProps {
  parameters: DiaryDsemPlotParameter[]
}

const WIDTH = 520
const HEIGHT = 180
const PAD = 28
const CHAIN_COLORS = ['#2563eb', '#dc2626', '#052796', '#7c3aed', '#d97706', '#0891b2']

function extent(values: number[]) {
  let minimum = Number.POSITIVE_INFINITY
  let maximum = Number.NEGATIVE_INFINITY
  for (const value of values) {
    if (value < minimum) minimum = value
    if (value > maximum) maximum = value
  }
  if (!Number.isFinite(minimum) || !Number.isFinite(maximum)) return [0, 1] as const
  if (minimum === maximum) return [minimum - 0.5, maximum + 0.5] as const
  return [minimum, maximum] as const
}

function scale(value: number, minimum: number, maximum: number, start: number, end: number) {
  return start + ((value - minimum) / (maximum - minimum)) * (end - start)
}

function tracePoints(
  iterations: number[],
  values: number[],
  iterationExtent: readonly [number, number],
  valueExtent: readonly [number, number],
) {
  return values.map((value, index) => [
    scale(iterations[index] ?? index, iterationExtent[0], iterationExtent[1], PAD, WIDTH - PAD),
    scale(value, valueExtent[0], valueExtent[1], HEIGHT - PAD, PAD),
  ].join(',')).join(' ')
}

function densityPoints(values: number[], valueExtent: readonly [number, number]) {
  const bins = 36
  const counts = Array.from({ length: bins }, () => 0)
  for (const value of values) {
    const relative = (value - valueExtent[0]) / (valueExtent[1] - valueExtent[0])
    const index = Math.min(bins - 1, Math.max(0, Math.floor(relative * bins)))
    counts[index] += 1
  }
  const maximum = Math.max(...counts, 1)
  return counts.map((count, index) => [
    scale(index, 0, bins - 1, PAD, WIDTH - PAD),
    scale(count, 0, maximum, HEIGHT - PAD, PAD),
  ].join(',')).join(' ')
}

export function DiaryDsemPlots({ parameters }: DiaryDsemPlotsProps) {
  if (!parameters.length) return null
  return (
    <section className="analysis-result-subsection" aria-labelledby="dsem-plots-heading">
      <h3 id="dsem-plots-heading">MCMC 迹线与后验分布</h3>
      <p className="method-note">
        图中使用每链等距抽取的有限 draws；Excel 导出包含相同绘图数据和可编辑附录图。
      </p>
      <div className="dsem-plot-grid">
        {parameters.map((parameter) => {
          const allValues = parameter.chains.flatMap((chain) => chain.values)
          const allIterations = parameter.chains.flatMap((chain) => chain.iterations)
          const valueExtent = extent(allValues)
          const iterationExtent = extent(allIterations)
          const traceTitleId = `${parameter.id}-trace-title`
          const densityTitleId = `${parameter.id}-density-title`
          return (
            <article key={parameter.id} className="dsem-plot-card">
              <h4>{parameter.label}</h4>
              <svg
                viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                role="img"
                aria-labelledby={traceTitleId}
              >
                <title id={traceTitleId}>{parameter.label} MCMC 迹线图</title>
                <line x1={PAD} y1={HEIGHT - PAD} x2={WIDTH - PAD} y2={HEIGHT - PAD} />
                <line x1={PAD} y1={PAD} x2={PAD} y2={HEIGHT - PAD} />
                {parameter.chains.map((chain, index) => (
                  <polyline
                    key={chain.chain}
                    points={tracePoints(
                      chain.iterations,
                      chain.values,
                      iterationExtent,
                      valueExtent,
                    )}
                    fill="none"
                    stroke={CHAIN_COLORS[index % CHAIN_COLORS.length]}
                    strokeWidth="1.2"
                    opacity="0.8"
                  />
                ))}
              </svg>
              <svg
                viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
                role="img"
                aria-labelledby={densityTitleId}
              >
                <title id={densityTitleId}>{parameter.label} 后验分布图</title>
                <line x1={PAD} y1={HEIGHT - PAD} x2={WIDTH - PAD} y2={HEIGHT - PAD} />
                <polyline
                  points={densityPoints(allValues, valueExtent)}
                  fill="none"
                  stroke="#334155"
                  strokeWidth="2"
                />
              </svg>
            </article>
          )
        })}
      </div>
    </section>
  )
}
