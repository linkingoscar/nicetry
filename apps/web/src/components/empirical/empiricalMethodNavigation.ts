import type { ResolvedAnalysisContext } from '../../types/analysis-context'
import type { EmpiricalConfigValue } from './empiricalConfigTypes'
import { createDefaultPanel, createEmptyWaves } from './LongitudinalPanelConfig.utils'
import { createDiaryMultilevelDefault, diaryAnalysisTypePatch } from './DiaryMultilevelConfigSections'
import { DEFAULT_DIARY_POWER } from './DiaryPowerConfig'

// Use the current draft as the base. The caller confirms any changes before saving.
export function configForMethod(config: EmpiricalConfigValue, sliceId: string, context?: ResolvedAnalysisContext | null): EmpiricalConfigValue {
  const roles = context?.structure?.roles
  const subjects = roles?.subjectId ? [{ id: roles.subjectId, label: roles.subjectId }] : []
  if (sliceId.startsWith('empirical.panel.')) {
    const panel = config.longitudinalPanel ?? createDefaultPanel(subjects, roles?.subjectId, roles?.waveCount)
    const method = sliceId.slice('empirical.panel.'.length)
    let next = panel
    if (method === 'clpm' || method === 'ri_clpm' || method === 'lcm_sr') {
      const minimum = method === 'lcm_sr' ? 5 : 3
      next = { ...panel, modelType: method,
        waves: panel.waves.length < minimum ? [...panel.waves, ...createEmptyWaves(minimum).slice(panel.waves.length)] : panel.waves,
        measurementMode: method === 'lcm_sr' ? 'latent_items' : panel.measurementMode,
        growthShape: method === 'lcm_sr' ? panel.growthShape : 'linear',
        powerAnalysis: method === 'ri_clpm' ? panel.powerAnalysis : null }
    } else if (method === 'invariance' || method === 'ulmc_sensitivity') {
      next = { ...panel, measurementMode: 'latent_items', invarianceLevel: panel.invarianceLevel === 'none' ? 'strict' : panel.invarianceLevel,
        cmbSensitivity: method === 'ulmc_sensitivity' ? 'global_ulmc' : panel.cmbSensitivity }
    }
    return { ...config, longitudinalPanel: next }
  }
  if (sliceId.startsWith('empirical.diary.')) {
    const diary = config.diaryMultilevel ?? createDiaryMultilevelDefault(subjects, roles?.subjectId, roles?.timeId)
    const method = sliceId.slice('empirical.diary.'.length)
    const type = method === 'dsem' ? 'bayesian_dsem' : method === 'multilevel_mediation' ? 'mediation' : method === 'glmm' ? 'glmm' : 'lmm'
    const next = diary.analysisType === type ? { ...diary } : { ...diary, ...diaryAnalysisTypePatch(diary, type) }
    if (method === 'cross_classified_gaussian') {
      next.clusterStructure = 'cross_classified'
      next.crossClassVariableId = roles?.clusterId ?? next.crossClassVariableId
    }
    if (method === 'mi') next.missingStrategy = 'multilevel_mi'
    if (method === 'power') next.powerAnalysis ??= { ...DEFAULT_DIARY_POWER }
    return { ...config, diaryMultilevel: next }
  }
  return config
}
