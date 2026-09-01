import type { EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'

export interface WorkbenchTarget {
  view: 'empirical' | 'model'
  tab?: EmpiricalResultTab
  sliceId: string
  label: string
}

export interface MethodRequest {
  sliceId: string
  label: string
  contextHash: string
  key: number
}

export interface EmpiricalTabRequest {
  tab: EmpiricalResultTab
  key: number
  method?: MethodRequest
}
