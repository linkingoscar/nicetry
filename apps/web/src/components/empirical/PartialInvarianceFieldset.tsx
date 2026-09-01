import type { LongitudinalPanelOptions } from '../../types'

interface PartialInvarianceFieldsetProps {
  value: LongitudinalPanelOptions
  positionCounts: { x: number; y: number }
  onTogglePosition: (position: string) => void
}

export function PartialInvarianceFieldset({
  value,
  positionCounts,
  onTogglePosition,
}: PartialInvarianceFieldsetProps) {
  if (value.measurementMode !== 'latent_items' || positionCounts.x + positionCounts.y <= 0) {
    return null
  }
  return (
    <fieldset className="analysis-check-grid">
      <legend>理论预先指定的部分等值释放位置（可选）</legend>
      {(['x', 'y'] as const).flatMap((construct) => (
        Array.from({ length: positionCounts[construct] }, (_, index) => {
          const position = `${construct}:${index + 1}`
          return (
            <label key={position}>
              <input
                type="checkbox"
                checked={value.partialInvariancePositions.includes(position)}
                onChange={() => onTogglePosition(position)}
              />
              {construct.toUpperCase()} 第 {index + 1} 个对应题项
            </label>
          )
        })
      ))}
    </fieldset>
  )
}
