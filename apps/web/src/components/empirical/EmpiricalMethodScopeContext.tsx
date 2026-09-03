import { createContext, useContext, type ReactNode } from 'react'
import type { DiaryMultilevelOptions, LongitudinalPanelOptions } from '../../types'

const EmpiricalMethodScopeContext = createContext<string | null>(null)

export function EmpiricalMethodScopeProvider({
  methodSliceId,
  children,
}: {
  methodSliceId?: string | null
  children: ReactNode
}) {
  return (
    <EmpiricalMethodScopeContext.Provider value={methodSliceId ?? null}>
      {children}
    </EmpiricalMethodScopeContext.Provider>
  )
}

export function useEmpiricalMethodSliceId(): string | null {
  return useContext(EmpiricalMethodScopeContext)
}

export function lockedLongitudinalModelType(
  sliceId?: string | null,
): LongitudinalPanelOptions['modelType'] | null {
  if (sliceId === 'empirical.panel.clpm') return 'clpm'
  if (sliceId === 'empirical.panel.ri_clpm') return 'ri_clpm'
  if (sliceId === 'empirical.panel.lcm_sr') return 'lcm_sr'
  return null
}

export function lockedDiaryAnalysisType(
  sliceId?: string | null,
): DiaryMultilevelOptions['analysisType'] | null {
  if (!sliceId?.startsWith('empirical.diary.')) return null
  const method = sliceId.slice('empirical.diary.'.length)
  if (method === 'dsem') return 'bayesian_dsem'
  if (method === 'multilevel_mediation') return 'mediation'
  if (method === 'glmm') return 'glmm'
  return 'lmm'
}
