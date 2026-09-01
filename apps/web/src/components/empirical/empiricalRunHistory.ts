import type { EmpiricalProcedure } from '../../types/empirical-types'
import { empiricalProcedures } from './empiricalProcedures'

export interface EmpiricalRunEntry { id: string; procedure: EmpiricalProcedure; createdAt: string }
export function readEmpiricalHistory(key: string): EmpiricalRunEntry[] {
  try {
    const value: unknown = JSON.parse(localStorage.getItem(key) ?? '[]')
    if (!Array.isArray(value)) return []
    return value.filter((v): v is EmpiricalRunEntry => v && typeof v.id === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(v.id)
      && empiricalProcedures.some((p) => p.id === v.procedure) && typeof v.createdAt === 'string').slice(0, 30)
  } catch { return [] }
}
export function saveEmpiricalHistory(key: string, value: EmpiricalRunEntry[]) {
  try { localStorage.setItem(key, JSON.stringify(value.slice(0, 30))) } catch { /* Server jobs remain persisted if local storage is unavailable. */ }
}
