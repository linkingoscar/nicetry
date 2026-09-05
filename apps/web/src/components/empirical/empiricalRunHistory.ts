import type { EmpiricalProcedure } from '../../types/empirical-types'
import { empiricalProcedures } from './empiricalProcedures'

export interface EmpiricalRunEntry {
  id: string
  procedure: EmpiricalProcedure
  createdAt: string
  analysisId?: string
  methodId?: string
}

const ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/
const METHOD_ID_PATTERN = /^[A-Za-z0-9_.-]{1,160}$/

export function readEmpiricalHistory(key: string): EmpiricalRunEntry[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    if (!Array.isArray(value)) return []
    return value.flatMap((raw): EmpiricalRunEntry[] => {
      if (!raw || typeof raw !== 'object') return []
      const entry = raw as Record<string, unknown>
      if (typeof entry.id !== 'string' || !ID_PATTERN.test(entry.id)) return []
      if (typeof entry.procedure !== 'string' || !empiricalProcedures.some((p) => p.id === entry.procedure)) return []
      if (typeof entry.createdAt !== 'string') return []

      const normalized: EmpiricalRunEntry = {
        id: entry.id,
        procedure: entry.procedure as EmpiricalProcedure,
        createdAt: entry.createdAt,
      }
      if (typeof entry.analysisId === 'string' && ID_PATTERN.test(entry.analysisId)) {
        normalized.analysisId = entry.analysisId
      }
      if (typeof entry.methodId === 'string' && METHOD_ID_PATTERN.test(entry.methodId)) {
        normalized.methodId = entry.methodId
      }
      return [normalized]
    }).slice(0, 30)
  } catch { return [] }
}

export function saveEmpiricalHistory(key: string, value: EmpiricalRunEntry[]) {
  try { localStorage.setItem(key, JSON.stringify(value.slice(0, 30))) } catch { /* Server jobs remain persisted if local storage is unavailable. */ }
}
