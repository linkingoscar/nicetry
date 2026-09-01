import type { NodeRole } from '../../types'

import { processPresets } from './processPresets.generated'
import { presetGroup, type ProcessNumber } from './processPresetGraph'

export type ModelTemplate = `model_${ProcessNumber}`

const familiarLabels: Partial<Record<ModelTemplate, string>> = {
  model_1: 'Model 1 · 单一调节',
  model_2: 'Model 2 · 双调节',
  model_3: 'Model 3 · 三阶交互',
  model_4: 'Model 4 · 单一中介',
  model_5: 'Model 5 · 中介 + 直接效应调节',
  model_6: 'Model 6 · 链式中介',
  model_7: 'Model 7 · 第一阶段调节中介',
  model_8: 'Model 8 · 双阶段调节中介 (第一阶段与直接路径被调节)',
  model_14: 'Model 14 · 第二阶段调节中介',
  model_15: 'Model 15 · 双阶段调节中介 (第二阶段与直接路径被调节)',
  model_21: 'Model 21 · 双调节变量的两阶段调节中介',
  model_22: 'Model 22 · 双调节变量的全路径调节中介',
  model_58: 'Model 58 · 第一、第二阶段同时调节',
  model_59: 'Model 59 · 全路径调节中介',
}

export const templateLabels = Object.fromEntries(processPresets.map(preset => {
  const key: ModelTemplate = `model_${preset.number}`
  return [key, familiarLabels[key] ?? `Model ${preset.number} · ${presetGroup(preset)}`]
})) as Record<ModelTemplate, string>

export const modelTypeLabels: Record<ModelTemplate | 'sem', string> = {
  ...templateLabels,
  sem: 'SEM · 结构方程模型',
}

const SUPPORTED_MODEL_TEMPLATES = new Set<string>(Object.keys(templateLabels))

export function isModelTemplate(value: string | null | undefined): value is ModelTemplate {
  return Boolean(value && SUPPORTED_MODEL_TEMPLATES.has(value))
}

export const roleLabels: Record<NodeRole, string> = {
  x: 'X · 自变量',
  m: 'M · 中介',
  y: 'Y · 结果',
  w: 'W · 调节',
  z: 'Z',
  covariate: '控制变量',
}
