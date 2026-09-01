import type { LongitudinalPanelOptions } from '../../types'

export interface Candidate {
  id: string
  label: string
}

export interface LongitudinalItemGroup {
  id: string
  label: string
  itemIds: string[]
}

export interface LongitudinalPanelConfigProps {
  value: LongitudinalPanelOptions | null
  variables: Candidate[]
  itemGroups: LongitudinalItemGroup[]
  subjectCandidates: Candidate[]
  defaultSubjectId?: string | null
  defaultWaveCount?: number | null
  onChange: (value: LongitudinalPanelOptions | null) => void
}
