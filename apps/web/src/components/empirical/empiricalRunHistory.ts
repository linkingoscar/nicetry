import type { EmpiricalProcedure } from '../../types/empirical-types'
import { empiricalProcedures } from './empiricalProcedures'

export interface EmpiricalRunEntry {
  id: string
  procedure: EmpiricalProcedure
  createdAt: string
  analysisId?: string
}

const ID_PATTERN = /^[A-Za-z0-9_-]{1,128}$/

export function readEmpiricalHistory(key: string): EmpiricalRunEntry[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    if (!Array.isArray(value)) return []
    return value.filter((v): v is EmpiricalRunEntry => v && typeof v.id === 'string' && ID_PATTERN.test(v.id)
      && empiricalProcedures.some((p) => p.id === v.procedure) && typeof v.createdAt === 'string'
      && (v.analysisId === undefined || (typeof v.analysisId === 'string' && ID_PATTERN.test(v.analysisId)))).slice(0, 30)
  } catch { return [] }
}

export function saveEmpiricalHistory(key: string, value: EmpiricalRunEntry[]) {
  try { localStorage.setItem(key, JSON.stringify(value.slice(0, 30))) } catch { /* Server jobs remain persisted if local storage is unavailable. */ }
}
