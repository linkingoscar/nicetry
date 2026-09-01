import type { DiaryMultilevelOptions } from '../../types'
import type { LongitudinalItemGroup } from './LongitudinalPanelConfig'
import { DiaryComplianceWindowSection } from './DiaryComplianceWindowSection'
import { DiaryModelEstimationSection } from './DiaryModelEstimationSection'
import { DiaryReliabilitySection } from './DiaryReliabilitySection'
import { DiaryTemporalDynamicsSection } from './DiaryTemporalDynamicsSection'

interface Candidate {
  id: string
  label: string
}

interface DiaryTemporalQualityConfigProps {
  value: DiaryMultilevelOptions
  variables: Candidate[]
  itemGroups: LongitudinalItemGroup[]
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryTemporalQualityConfig({
  value,
  variables,
  itemGroups,
  onChange,
}: DiaryTemporalQualityConfigProps) {
  return (
    <div className="longitudinal-evidence-stack">
      <DiaryTemporalDynamicsSection value={value} variables={variables} onChange={onChange} />
      <DiaryComplianceWindowSection value={value} variables={variables} onChange={onChange} />
      <DiaryReliabilitySection value={value} itemGroups={itemGroups} onChange={onChange} />
      <DiaryModelEstimationSection value={value} onChange={onChange} />
    </div>
  )
}
