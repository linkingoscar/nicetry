import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'

export interface WorkbenchTarget {
  view: 'empirical' | 'model'
  tab?: EmpiricalResultTab
  sliceId: string
  label: string
  procedure?: EmpiricalProcedure
}

export interface MethodRequest {
  sliceId: string
  label: string
  contextHash: string
  key: number
  procedure?: EmpiricalProcedure
}

export interface EmpiricalTabRequest {
  tab: EmpiricalResultTab
  key: number
  method?: MethodRequest
}
