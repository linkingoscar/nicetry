export type HeatmapPalette = 'okabe_ito' | 'viridis' | 'cividis'

export function getScientificCellColor(
  value: number | null,
  palette: HeatmapPalette = 'okabe_ito',
): string {
  if (value === null || Number.isNaN(value)) return '#1e293b'
  const val = Math.max(-1, Math.min(1, value))

  if (palette === 'viridis') {
    const t = (val + 1) / 2
    const r = Math.round(68 + t * (253 - 68))
    const g = Math.round(1 + t * (231 - 1))
    const b = Math.round(84 + t * (37 - 84))
    return `rgb(${r}, ${g}, ${b})`
  }

  if (palette === 'cividis') {
    const t = (val + 1) / 2
    const r = Math.round(0 + t * (230 - 0))
    const g = Math.round(32 + t * (230 - 32))
    const b = Math.round(77 + t * (120 - 77))
    return `rgb(${r}, ${g}, ${b})`
  }

  // okabe_ito: Blue (-1) -> White (0) -> Vermilion (+1)
  if (val > 0) {
    const t = val
    const r = Math.round(255 + t * (213 - 255))
    const g = Math.round(255 + t * (94 - 255))
    const b = Math.round(255 + t * (0 - 255))
    return `rgb(${r}, ${g}, ${b})`
  } else {
    const t = -val
    const r = Math.round(255 + t * (86 - 255))
    const g = Math.round(255 + t * (180 - 255))
    const b = Math.round(255 + t * (233 - 255))
    return `rgb(${r}, ${g}, ${b})`
  }
}
