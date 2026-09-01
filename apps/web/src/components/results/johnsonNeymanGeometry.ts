import type { JohnsonNeymanResult } from '../../types/models'

type JNGrid = NonNullable<JohnsonNeymanResult['grid']>

export const JN_REGION_LABELS = {
  positive: '显著正向',
  negative: '显著负向',
  not_significant: '不显著',
} as const

export interface JNHoverState {
  moderatorValue: number
  effect: number
  lower: number
  upper: number
  status: 'positive' | 'negative' | 'not_significant'
  cx: number
  cy: number
}

export interface JNGeometry {
  xScale: (value: number) => number
  yScale: (value: number) => number
  effectPoints: string
  lowerPoints: string
  upperPoints: string
  chartMin: number
  chartMax: number
}

export function buildJNGeometry(
  result: JohnsonNeymanResult,
  grid: JNGrid,
  width: number,
  height: number,
  left: number,
  right: number,
  top: number,
  bottom: number,
): JNGeometry | null {
  if (!grid.length) return null
  const xMin = result.observedMinimum
  const xMax = result.observedMaximum
  const values = grid.flatMap((row) => [row.effect, row.lower, row.upper, 0])
  const yMin = Math.min(...values)
  const yMax = Math.max(...values)
  const yPadding = Math.max(Number.EPSILON, yMax - yMin) * 0.08
  const chartMin = yMin - yPadding
  const chartMax = yMax + yPadding

  const xScale = (value: number) =>
    left + ((value - xMin) / Math.max(Number.EPSILON, xMax - xMin)) * (width - left - right)
  const yScale = (value: number) =>
    height - bottom - ((value - chartMin) / Math.max(Number.EPSILON, chartMax - chartMin)) * (height - top - bottom)
  const getPoints = (field: 'effect' | 'lower' | 'upper') =>
    grid.map((row) => `${xScale(row.moderatorValue)},${yScale(row[field])}`).join(' ')

  return {
    xScale,
    yScale,
    effectPoints: getPoints('effect'),
    lowerPoints: getPoints('lower'),
    upperPoints: getPoints('upper'),
    chartMin,
    chartMax,
  }
}

export function nearestJNHover(
  geometry: JNGeometry,
  grid: JNGrid,
  mouseX: number,
): JNHoverState | null {
  let nearest: JNHoverState | null = null
  let minDist = Infinity
  for (const row of grid) {
    const cx = geometry.xScale(row.moderatorValue)
    const dist = Math.abs(mouseX - cx)
    if (dist < minDist) {
      minDist = dist
      nearest = {
        moderatorValue: row.moderatorValue,
        effect: row.effect,
        lower: row.lower,
        upper: row.upper,
        status: row.significant ? (row.effect >= 0 ? 'positive' : 'negative') : 'not_significant',
        cx,
        cy: geometry.yScale(row.effect),
      }
    }
  }
  return minDist < 40 ? nearest : null
}
