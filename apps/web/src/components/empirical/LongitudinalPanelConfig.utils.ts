import type { LongitudinalPanelOptions } from '../../types'
import type { Candidate, LongitudinalItemGroup } from './LongitudinalPanelConfig.types'

export function createEmptyWaves(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    label: `T${index + 1}`,
    timeValue: index,
    xVariableId: null,
    yVariableId: null,
    xItemIds: [],
    yItemIds: [],
  }))
}

export function createDefaultPanel(
  subjectCandidates: Candidate[],
  defaultSubjectId?: string | null,
  defaultWaveCount?: number | null,
): LongitudinalPanelOptions {
  const subjectId = defaultSubjectId && subjectCandidates.some((candidate) => candidate.id === defaultSubjectId)
    ? defaultSubjectId
    : subjectCandidates[0]?.id ?? ''
  const waveCount = Number.isInteger(defaultWaveCount) && defaultWaveCount && defaultWaveCount >= 2
    ? Math.min(defaultWaveCount, 10)
    : 3
  return {
    modelType: 'ri_clpm',
    measurementMode: 'observed_scores',
    subjectVariableId: subjectId,
    waves: createEmptyWaves(waveCount),
    estimator: 'MLR',
    missing: 'fiml',
    constrainAcrossTime: false,
    growthShape: 'linear',
    indicatorScale: 'continuous',
    invarianceLevel: 'strict',
    partialInvariancePositions: [],
    cmbSensitivity: 'none',
    compareCompetingModels: false,
    runRobustnessChecks: false,
    powerAnalysis: null,
  }
}

export function matchingGroup(groups: LongitudinalItemGroup[], itemIds: string[]) {
  return groups.find((group) => (
    group.itemIds.length === itemIds.length
    && group.itemIds.every((itemId, index) => itemId === itemIds[index])
  ))?.id ?? ''
}
