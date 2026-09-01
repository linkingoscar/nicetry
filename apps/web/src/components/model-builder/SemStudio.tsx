import type { DatasetVersion, ModelSpec, ModelVariable } from '../../types'
import { SemStudioEstimationPanel } from './SemStudioEstimationPanel'
import { SemStudioMeasurementEditor } from './SemStudioMeasurementEditor'

interface SemStudioProps {
  model: ModelSpec
  variables: ModelVariable[]
  indicatorCandidates: DatasetVersion['variables']
  updateModel: (updater: (current: ModelSpec) => ModelSpec) => void
  showMeasurement?: boolean
}

export function SemStudio({
  model,
  variables,
  indicatorCandidates,
  updateModel,
  showMeasurement = true,
}: SemStudioProps) {
  return (
    <>
      {showMeasurement ? <SemStudioMeasurementEditor
        model={model}
        indicatorCandidates={indicatorCandidates}
        updateModel={updateModel}
      /> : null}
      <SemStudioEstimationPanel
        model={model}
        variables={variables}
        indicatorCandidates={indicatorCandidates}
        updateModel={updateModel}
      />
    </>
  )
}
