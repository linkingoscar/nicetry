import type { LongitudinalPanelOptions } from '../../types'
import type { Candidate, LongitudinalItemGroup } from './LongitudinalPanelConfig.types'
import { matchingGroup } from './LongitudinalPanelConfig.utils'

interface LongitudinalWaveTableProps {
  value: LongitudinalPanelOptions
  variables: Candidate[]
  itemGroups: LongitudinalItemGroup[]
  onUpdateWave: (
    index: number,
    patch: Partial<LongitudinalPanelOptions['waves'][number]>,
  ) => void
  onRemoveWave: (index: number) => void
}

export function LongitudinalWaveTable({
  value,
  variables,
  itemGroups,
  onUpdateWave,
  onRemoveWave,
}: LongitudinalWaveTableProps) {
  return (
    <div className="table-wrap">
      <table className="result-table empirical-table longitudinal-wave-table">
        <thead>
          <tr>
            <th>波次</th><th>时间值</th>
            <th>{value.measurementMode === 'latent_items' ? 'X 测量构念' : 'X 变量'}</th>
            <th>{value.measurementMode === 'latent_items' ? 'Y 测量构念' : 'Y 变量'}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {value.waves.map((wave, index) => (
            <tr key={wave.label}>
              <td>
                <input
                  aria-label={`波次 ${index + 1} 标签`}
                  value={wave.label}
                  onChange={(event) => onUpdateWave(index, { label: event.target.value })}
                />
              </td>
              <td>
                <input
                  aria-label={`${wave.label} 时间值`}
                  type="number"
                  step="0.5"
                  value={wave.timeValue}
                  onChange={(event) => onUpdateWave(index, {
                    timeValue: Number(event.target.value),
                  })}
                />
              </td>
              <td>
                {value.measurementMode === 'latent_items' ? (
                  <select
                    aria-label={`${wave.label} X 测量构念`}
                    value={matchingGroup(itemGroups, wave.xItemIds)}
                    onChange={(event) => onUpdateWave(index, {
                      xItemIds: itemGroups.find((group) => group.id === event.target.value)?.itemIds ?? [],
                    })}
                  >
                    <option value="">选择 X 构念</option>
                    {itemGroups.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.label}（{group.itemIds.length}题）
                      </option>
                    ))}
                  </select>
                ) : (
                  <select
                    aria-label={`${wave.label} X 变量`}
                    value={wave.xVariableId ?? ''}
                    onChange={(event) => onUpdateWave(index, {
                      xVariableId: event.target.value || null,
                    })}
                  >
                    <option value="">选择 X</option>
                    {variables.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
                    ))}
                  </select>
                )}
              </td>
              <td>
                {value.measurementMode === 'latent_items' ? (
                  <select
                    aria-label={`${wave.label} Y 测量构念`}
                    value={matchingGroup(itemGroups, wave.yItemIds)}
                    onChange={(event) => onUpdateWave(index, {
                      yItemIds: itemGroups.find((group) => group.id === event.target.value)?.itemIds ?? [],
                    })}
                  >
                    <option value="">选择 Y 构念</option>
                    {itemGroups.map((group) => (
                      <option key={group.id} value={group.id}>
                        {group.label}（{group.itemIds.length}题）
                      </option>
                    ))}
                  </select>
                ) : (
                  <select
                    aria-label={`${wave.label} Y 变量`}
                    value={wave.yVariableId ?? ''}
                    onChange={(event) => onUpdateWave(index, {
                      yVariableId: event.target.value || null,
                    })}
                  >
                    <option value="">选择 Y</option>
                    {variables.map((candidate) => (
                      <option key={candidate.id} value={candidate.id}>{candidate.label}</option>
                    ))}
                  </select>
                )}
              </td>
              <td>
                <button
                  type="button"
                  className="secondary-button"
                  disabled={value.waves.length <= (
                    value.modelType === 'lcm_sr' ? 5 : value.modelType === 'ri_clpm' ? 3 : 2
                  )}
                  onClick={() => onRemoveWave(index)}
                >
                  删除
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
