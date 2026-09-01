import type { DatasetVariable } from '../../types'

export interface RoleSelection {
  subjectId: string
  clusterId: string
  timeId: string
  groupId: string
  treatmentId: string
  dataLayout: 'long' | 'wide'
  waveCount: string
}

export const ROLE_LABELS: Array<[keyof RoleSelection, string]> = [
  ['subjectId', '个体 / 研究对象 ID'],
  ['clusterId', '聚类 / Level 2 ID'],
  ['timeId', '波次 / 时间变量'],
  ['groupId', '分组变量'],
  ['treatmentId', '处理 / 暴露变量'],
]

interface RoleBindingSelectorProps {
  roles: RoleSelection
  variables: DatasetVariable[]
  isPanel: boolean
  isWidePanel: boolean
  subjectRequired: boolean
  requiresSubjectAndTime: boolean
  requiresCluster: boolean
  requiresTreatmentOrGroup: boolean
  updateRole: (role: keyof RoleSelection, value: string) => void
  updateLayout: (layout: 'long' | 'wide') => void
}

export function RoleBindingSelector({
  roles,
  variables,
  isPanel,
  isWidePanel,
  subjectRequired,
  requiresSubjectAndTime,
  requiresCluster,
  requiresTreatmentOrGroup,
  updateRole,
  updateLayout,
}: RoleBindingSelectorProps) {
  return (
    <div className="structure-role-grid">
      {ROLE_LABELS.map(([role, label]) => {
        const visible =
          role === 'subjectId' ||
          (role === 'timeId' && requiresSubjectAndTime) ||
          (role === 'clusterId' && requiresCluster) ||
          ((role === 'groupId' || role === 'treatmentId') && requiresTreatmentOrGroup)

        if (!visible) return null

        const required =
          (role === 'subjectId' && subjectRequired) ||
          (role === 'timeId' && requiresSubjectAndTime) ||
          (role === 'clusterId' && requiresCluster) ||
          ((role === 'groupId' || role === 'treatmentId') && requiresTreatmentOrGroup)

        const options = variables.map(variable => (
          <option key={variable.id} value={variable.id}>
            {variable.originalName} ({variable.label})
          </option>
        ))

        return (
          <label key={role}>
            {label} {required ? <strong>（必填）</strong> : <span>（可选）</span>}
            <select
              value={roles[role]}
              onChange={event => updateRole(role, event.target.value)}
            >
              <option value="">不指定</option>{options}
            </select>
          </label>
        )
      })}
      {isPanel ? (
        <label>
          面板数据布局 <strong>（必填）</strong>
          <select
            value={roles.dataLayout}
            onChange={event => updateLayout(event.target.value === 'wide' ? 'wide' : 'long')}
          >
            <option value="long">长格式：对象 × 波次多行</option>
            <option value="wide">宽格式：每个对象一行，显式声明波次数</option>
          </select>
        </label>
      ) : null}
      {isWidePanel ? (
        <label>
          波次数（wave count） <strong>（必填）</strong>
          <input
            type="number"
            min={2}
            max={10}
            step={1}
            value={roles.waveCount}
            onChange={event => updateRole('waveCount', event.target.value)}
            placeholder="例如 5"
          />
        </label>
      ) : null}
    </div>
  )
}
