import type { ApplicableCapability } from '../types/analysis-context'

export type MethodAvailabilityState = 'ready' | 'needs-setup' | 'not-applicable' | 'unavailable'

export interface MethodAvailability {
  state: MethodAvailabilityState
  label: string
  reason: string | null
}

export function resolveMethodAvailability(capability: ApplicableCapability): MethodAvailability {
  if (!capability.executionAvailable) {
    return {
      state: 'unavailable',
      label: '当前不可运行',
      reason: capability.blockedReason ?? '当前版本尚未开放执行。',
    }
  }

  if (capability.applicable) {
    return {
      state: 'ready',
      label: '可直接配置',
      reason: null,
    }
  }

  if (capability.missingRequirements.length > 0) {
    return {
      state: 'needs-setup',
      label: '需要补充设置',
      reason: capability.blockedReason ?? `还需完成：${capability.missingRequirements.join('、')}`,
    }
  }

  return {
    state: 'not-applicable',
    label: '当前数据不适用',
    reason: capability.blockedReason ?? '当前数据结构或研究设计不满足该方法的适用范围。',
  }
}
