import type { DatasetVersion, MeasurementVersion } from '../../types'
import type { EmpiricalProcedure } from '../../types/empirical-types'
import { empiricalDraftKey, readEmpiricalDraft, type EmpiricalDraft } from '../empirical/empiricalDrafts'

export interface OutputDraftStatus {
  activeRunId: string | null
  dirtySinceLastRun: boolean
  hasSavedDraft: boolean
}

function toStatus(draft: EmpiricalDraft | null): OutputDraftStatus {
  if (!draft) return { activeRunId: null, dirtySinceLastRun: false, hasSavedDraft: false }
  return {
    activeRunId: draft.activeRunId,
    dirtySinceLastRun: Boolean(
      draft.lastRunConfig && JSON.stringify(draft.config) !== JSON.stringify(draft.lastRunConfig),
    ),
    hasSavedDraft: true,
  }
}

export function empiricalDraftStatusForOutput(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  procedure: EmpiricalProcedure,
  latestRunId?: string,
): OutputDraftStatus {
  const pendingKey = empiricalDraftKey(dataset, measurement)
  const pendingDraft = readEmpiricalDraft(pendingKey, procedure)
  if (pendingDraft && (!latestRunId || pendingDraft.activeRunId === latestRunId)) return toStatus(pendingDraft)

  const prefix = pendingKey.endsWith(':pending') ? pendingKey.slice(0, -'pending'.length) : `${pendingKey}:`
  const suffix = `:${procedure}`
  const candidates: EmpiricalDraft[] = []
  for (let index = 0; index < localStorage.length; index += 1) {
    const storageKey = localStorage.key(index)
    if (!storageKey?.startsWith(prefix) || !storageKey.endsWith(suffix)) continue
    const draftKey = storageKey.slice(0, -suffix.length)
    const draft = readEmpiricalDraft(draftKey, procedure)
    if (draft) candidates.push(draft)
  }

  if (latestRunId) {
    const matching = candidates.find((draft) => draft.activeRunId === latestRunId)
    if (matching) return toStatus(matching)
    return toStatus(null)
  }
  return toStatus(candidates.length === 1 ? candidates[0] : null)
}
