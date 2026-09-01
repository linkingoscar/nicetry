import type { DiaryMultilevelOptions } from '../../types'
import type { LongitudinalItemGroup } from './LongitudinalPanelConfig'

interface DiaryReliabilitySectionProps {
  value: DiaryMultilevelOptions
  itemGroups: LongitudinalItemGroup[]
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryReliabilitySection({
  value,
  itemGroups,
  onChange,
}: DiaryReliabilitySectionProps) {
  const toggleReliability = (group: LongitudinalItemGroup) => {
    const selected = value.reliabilityConstructs.some(
      (construct) => construct.label === group.label
        && construct.itemIds.join('|') === group.itemIds.join('|'),
    )
    onChange({
      reliabilityConstructs: selected
        ? value.reliabilityConstructs.filter(
            (construct) => construct.label !== group.label
              || construct.itemIds.join('|') !== group.itemIds.join('|'),
          )
        : [...value.reliabilityConstructs, {
            label: group.label,
            itemIds: group.itemIds,
          }],
    })
  }

  if (!itemGroups.length) return null

  return (
    <fieldset className="analysis-variable-picker">
      <legend>计算被试内/被试间信度（可选）</legend>
      {itemGroups.map((group) => (
        <label key={group.id}>
          <input
            type="checkbox"
            checked={value.reliabilityConstructs.some(
              (construct) => construct.label === group.label
                && construct.itemIds.join('|') === group.itemIds.join('|'),
            )}
            onChange={() => toggleReliability(group)}
          />
          {group.label}（{group.itemIds.length}题）
        </label>
      ))}
    </fieldset>
  )
}
