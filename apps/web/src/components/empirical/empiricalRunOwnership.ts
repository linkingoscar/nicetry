import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { EmpiricalRunEntry } from './empiricalRunHistory'

export function filterEmpiricalRunHistoryForAnalysis(
  runs: EmpiricalRunEntry[],
  analysisProcedure?: EmpiricalProcedure,
  analysisId?: string | null,
  indexedRunIds?: ReadonlySet<string> | null,
): EmpiricalRunEntry[] {
  return runs.filter((entry) => {
    if (analysisProcedure && entry.procedure !== analysisProcedure) return false
    if (!analysisId) return true
    if (entry.analysisId) return entry.analysisId === analysisId
    return indexedRunIds?.has(entry.id) ?? false
  })
}
