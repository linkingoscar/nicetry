import type { DiaryMultilevelOptions } from '../../types'
import { DiaryDsemConfig } from './DiaryDsemConfig'
import { DiaryGlmmConfig } from './DiaryGlmmConfig'

interface Candidate {
  id: string
  label: string
}

interface DiaryAdvancedModelConfigProps {
  value: DiaryMultilevelOptions
  variables: Candidate[]
  onChange: (patch: Partial<DiaryMultilevelOptions>) => void
}

export function DiaryAdvancedModelConfig({
  value,
  variables,
  onChange,
}: DiaryAdvancedModelConfigProps) {
  if (value.analysisType === 'bayesian_dsem') {
    const dsem = value.dsem
    if (!dsem) return null
    return <DiaryDsemConfig dsem={dsem} onChange={onChange} />
  }

  if (!['lmm', 'glmm'].includes(value.analysisType)) return null
  return <DiaryGlmmConfig value={value} variables={variables} onChange={onChange} />
}
