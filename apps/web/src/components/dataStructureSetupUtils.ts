import type { DatasetVariable, StudyContext } from '../types'
import type {
  DatasetRoleBindings,
  DatasetStructureVersion,
} from '../types/study-context'

export interface RoleSelection {
  subjectId: string
  clusterId: string
  timeId: string
  groupId: string
  treatmentId: string
  dataLayout: 'long' | 'wide'
  waveCount: string
}

export type PersistedStructure = {
  id: string
  revision: number
  studyContextVersionId: string
  roles: DatasetRoleBindings
  status: DatasetStructureVersion['status']
  profile?: DatasetStructureVersion['profile'] | null
  warnings?: DatasetStructureVersion['warnings']
  overrideReason?: string | null
}

export const ROLE_LABELS: Array<[keyof RoleSelection, string]> = [
  ['subjectId', '个体 / 研究对象 ID'],
  ['clusterId', '聚类 / Level 2 ID'],
  ['timeId', '波次 / 时间变量'],
  ['groupId', '分组变量'],
  ['treatmentId', '处理 / 暴露变量'],
]

export const VARIABLE_ROLE_KEYS: Array<keyof Pick<RoleSelection, 'subjectId' | 'clusterId' | 'timeId' | 'groupId' | 'treatmentId'>> = [
  'subjectId', 'clusterId', 'timeId', 'groupId', 'treatmentId',
]

export function toBindings(roles: RoleSelection): DatasetRoleBindings {
  return {
    subjectId: roles.subjectId || null,
    clusterId: roles.clusterId || null,
    timeId: roles.timeId || null,
    groupId: roles.groupId || null,
    treatmentId: roles.treatmentId || null,
    dataLayout: roles.dataLayout,
    waveCount: roles.waveCount ? Number(roles.waveCount) : null,
  }
}

function firstVariableId(
  variables: DatasetVariable[],
  exactNames: string[],
  pattern?: RegExp,
): string {
  const exact = new Set(exactNames.map(name => name.toLowerCase()))
  const exactMatch = variables.find(variable => exact.has(variable.originalName.trim().toLowerCase()))
  if (exactMatch) return exactMatch.id
  return pattern ? variables.find(variable => pattern.test(variable.originalName))?.id ?? '' : ''
}

export function inferExampleRoles(context: StudyContext, variables: DatasetVariable[]): RoleSelection {
  const subjectId = firstVariableId(
    variables,
    ['subject_id', 'person_id', 'participant_id', 'respondent_id', 'id'],
    /(?:subject|person|participant|respondent|被试|受访).*(?:id)?$/i,
  )
  const timeId = firstVariableId(
    variables,
    ['day', 'time', 'time_id', 'wave', 'wave_id', 'occasion', 'occasion_id', 'date', 'timestamp'],
    /(?:^|[_-])(day|time|wave|occasion|date|timestamp)(?:[_-]|$)/i,
  )
  const clusterId = context.dependenceStructure === 'nested'
    ? firstVariableId(
      variables,
      ['cluster_id', 'team_id', 'class_id', 'school_id', 'site_id', 'level2_id'],
      /(?:cluster|team|class|school|site|level.?2).*(?:id)?$/i,
    )
    : ''
  const groupId = context.design !== 'observational'
    ? firstVariableId(variables, ['group', 'group_id', 'arm', 'condition'], /(?:^|[_-])(group|arm|condition)(?:[_-]|$)/i)
    : ''
  const treatmentId = context.design !== 'observational'
    ? firstVariableId(variables, ['intervention', 'treatment', 'treatment_id', 'exposure'], /(?:intervention|treatment|exposure)/i)
    : ''

  const waveNumbers = context.timeStructure === 'panel'
    ? [...new Set(variables.flatMap(variable => {
      const match = variable.originalName.match(/_t(\d+)(?:_i\d+)?$/i)
      return match ? [Number(match[1])] : []
    }))].sort((left, right) => left - right)
    : []
  const isWidePanel = waveNumbers.length >= 2

  return {
    subjectId,
    clusterId,
    timeId: isWidePanel ? '' : timeId,
    groupId,
    treatmentId,
    dataLayout: isWidePanel ? 'wide' : 'long',
    waveCount: isWidePanel ? String(waveNumbers.length) : '',
  }
}

export function fromBindings(
  roles: DatasetRoleBindings | undefined,
  knownVariableIds: Set<string>,
  context: StudyContext,
  variables: DatasetVariable[],
): RoleSelection {
  if (!roles) return inferExampleRoles(context, variables)
  const pickVariable = (value: string | null | undefined) => (
    typeof value === 'string' && knownVariableIds.has(value) ? value : ''
  )
  return {
    subjectId: pickVariable(roles?.subjectId),
    clusterId: pickVariable(roles?.clusterId),
    timeId: pickVariable(roles?.timeId),
    groupId: pickVariable(roles?.groupId),
    treatmentId: pickVariable(roles?.treatmentId),
    dataLayout: roles?.dataLayout === 'wide' ? 'wide' : 'long',
    waveCount: roles?.waveCount ? String(roles.waveCount) : '',
  }
}

export function sameRoles(left: DatasetRoleBindings | undefined, right: RoleSelection): boolean {
  const current = toBindings(right)
  return VARIABLE_ROLE_KEYS.every((key) => current[key] === left?.[key])
    && current.dataLayout === (left?.dataLayout ?? 'long')
    && current.waveCount === (left?.waveCount ?? null)
}

export function roleName(role: keyof RoleSelection): string {
  return ROLE_LABELS.find(([key]) => key === role)?.[1] ?? role
}
