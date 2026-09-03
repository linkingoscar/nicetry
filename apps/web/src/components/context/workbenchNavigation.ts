import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'

export interface WorkbenchTarget {
  view: 'empirical' | 'model'
  tab?: EmpiricalResultTab
  sliceId: string
  label: string
  procedure?: EmpiricalProcedure
  processModelNumber?: 1 | 4
}

export interface MethodRequest {
  sliceId: string
  label: string
  contextHash: string
  key: number
  procedure?: EmpiricalProcedure
  processModelNumber?: 1 | 4
}

export interface EmpiricalTabRequest {
  tab: EmpiricalResultTab
  key: number
  method?: MethodRequest
}
