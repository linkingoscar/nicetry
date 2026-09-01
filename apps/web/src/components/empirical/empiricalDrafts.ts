import type { DatasetVersion, MeasurementVersion } from '../../types'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import { empiricalProcedures } from './empiricalProcedures'

export interface EmpiricalDraft {
  config: EmpiricalConfigValue
  activeRunId: string | null
  lastRunConfig: EmpiricalConfigValue | null
  tabRequestKey?: number
}

export function empiricalDraftKey(dataset: DatasetVersion, measurement: MeasurementVersion | null, context?: ResolvedAnalysisContext | null): string {
  return `researchpath.empirical.draft.v1:${dataset.id}:${dataset.originalFile?.sha256 ?? ''}:${dataset.dictionary?.version ?? 0}:${(measurement?.version ?? null)}:${measurement?.derivedDataset.sha256 ?? ''}:${context?.contextHash ?? 'pending'}`
}

function validConfig(value: unknown): value is EmpiricalConfigValue {
  if (!value || typeof value !== 'object') return false
  const config = value as Record<string, unknown>
  return empiricalProcedures.some(p => p.id === config.procedure)
    && ['analysisVariableIds', 'constructIds', 'predictorVariableIds', 'controlVariableIds', 'responseSurfacePredictorIds'].every(key =>
      Array.isArray(config[key]) && config[key].length <= 10000 && config[key].every((id: unknown) => typeof id === 'string'))
    && ['correlationPAdjust', 'groupOmnibusPAdjust', 'multiplicityPAdjust'].every(key => ['BH', 'holm', 'none'].includes(String(config[key])))
    && typeof config.factorCount === 'number' && typeof config.confidenceLevel === 'number'
}

export function readEmpiricalDraft(key: string, procedure?: EmpiricalProcedure): EmpiricalDraft | null {
  try {
    const selected = procedure ?? localStorage.getItem(`${key}:selected`)
    if (!empiricalProcedures.some(p => p.id === selected)) return null
    const raw = localStorage.getItem(`${key}:${selected}`)
    if (!raw || raw.length > 500000) return null
    const value = JSON.parse(raw) as EmpiricalDraft
    if (!validConfig(value.config) || value.config.procedure !== selected
      || (value.lastRunConfig !== null && !validConfig(value.lastRunConfig))
      || (value.activeRunId !== null && (typeof value.activeRunId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(value.activeRunId)))) return null
    return value
  } catch { return null }
}

export function saveEmpiricalDraft(key: string, draft: EmpiricalDraft): boolean {
  try {
    localStorage.setItem(`${key}:${draft.config.procedure}`, JSON.stringify(draft))
    localStorage.setItem(`${key}:selected`, draft.config.procedure)
    return true
  } catch { return false }
}
