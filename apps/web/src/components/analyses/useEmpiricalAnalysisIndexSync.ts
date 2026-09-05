import { useEffect } from 'react'

import type { DatasetVersion, EmpiricalAnalysisJob, MeasurementVersion } from '../../types'
import { syncEmpiricalAnalysisRunDetail } from './analysisRunDetails'

export function useEmpiricalAnalysisIndexSync(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  job: EmpiricalAnalysisJob | undefined,
) {
  useEffect(() => {
    if (!job?.options.procedure) return
    syncEmpiricalAnalysisRunDetail(dataset, measurement, job)
  }, [dataset, job, measurement])
}
