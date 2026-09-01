import type { DatasetVersion, MeasurementVersion, ModelSpec } from '../types'
import type { TimeStructure } from '../types/study-context'
import { requestJson } from './client'

export interface DemoProjectPayload {
  dataset: DatasetVersion
  measurement: MeasurementVersion
  modelSpec: ModelSpec
}

export function loadDemoProject(timeStructure: TimeStructure = 'cross_sectional'): Promise<DemoProjectPayload> {
  return requestJson<DemoProjectPayload>('/api/v1/demo/load', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ timeStructure }),
  })
}
