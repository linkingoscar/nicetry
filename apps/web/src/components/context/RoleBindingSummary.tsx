import type { DatasetRoleBindings } from '../../types/analysis-context'

const ROLE_LABELS: Array<[keyof DatasetRoleBindings, string]> = [
  ['subjectId', 'subject / 个体'],
  ['clusterId', 'cluster / 聚类'],
  ['timeId', 'time / 时间'],
  ['groupId', 'group / 分组'],
  ['treatmentId', 'treatment / 处理'],
]

interface RoleBindingSummaryProps {
  roles: DatasetRoleBindings | null | undefined
}

export function RoleBindingSummary({ roles }: RoleBindingSummaryProps) {
  return (
    <dl className="context-role-list">
      {ROLE_LABELS.map(([key, label]) => (
        <div key={key}>
          <dt>{label}</dt>
          <dd>{roles?.[key] ?? '未绑定'}</dd>
        </div>
      ))}
    </dl>
  )
}
