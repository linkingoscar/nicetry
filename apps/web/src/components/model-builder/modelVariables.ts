import type { DatasetVariable, DatasetVersion, MeasurementVersion, ModelVariable } from '../../types'

function observedEncoding(variable: DatasetVariable): ModelVariable['encodingHint'] {
  const type = variable.confirmedType ?? variable.inferredType
  const levels = Object.keys(variable.valueLabels).length
    ? Object.keys(variable.valueLabels)
    : [...new Set(variable.sampleValues.filter((value) => value !== null).map(String))]
  if (type === 'nominal') {
    return {
      method: 'treatment',
      referenceLevel: levels[0] ?? null,
      levels,
      label: '虚拟编码（k−1）',
      reason: '无序类别默认使用处理编码，并保留一个参照组。',
    }
  }
  if (type === 'binary') {
    return {
      method: 'binary_indicator',
      referenceLevel: levels[0] ?? null,
      levels,
      label: '二元指示编码（0/1）',
      reason: '二分类变量按参照组=0、事件组=1 编码。',
    }
  }
  if (type === 'ordinal' || type === 'likert') {
    return {
      method: 'ordinal_score',
      levels,
      label: '有序得分编码',
      reason: '教育程度或 Likert 题按明确顺序映射为递增得分。',
    }
  }
  const looksLikeAge = /(^|[^a-z])(age|年龄|岁数)([^a-z]|$)/i.test(`${variable.originalName} ${variable.label}`)
  return {
    method: looksLikeAge ? 'mean_center' : 'as_is',
    label: looksLikeAge ? '均值中心化' : '原值连续变量',
    reason: looksLikeAge ? '年龄作为控制变量时默认中心化，使截距更容易解释。' : '连续变量保持原量尺；需要比较效应时可改为标准化。',
  }
}

export function buildModelVariables(
  dataset: DatasetVersion,
  measurement: MeasurementVersion,
): ModelVariable[] {
  const typeMap: Partial<Record<string, ModelVariable['dataType']>> = {
    continuous: 'continuous',
    binary: 'binary',
    nominal: 'nominal',
    ordinal: 'ordinal',
    likert: 'ordinal',
  }
  const scores = measurement.derivedDataset.scoreVariables.map((variable) => ({
    id: variable.id,
    label: variable.label,
    kind: 'scale_score' as const,
    dataType: 'continuous' as const,
    source: `测量版本 v${measurement.version}`,
    encodingHint: {
      method: 'as_is' as const,
      label: '量表合成分',
      reason: '优先使用已完成反向计分和缺失规则处理的构念得分。',
    },
  }))
  const observed = dataset.variables.flatMap((variable) => {
    const dataType = typeMap[variable.confirmedType ?? '']
    return dataType
      ? [{
          id: variable.id,
          label: variable.label,
          kind: 'observed' as const,
          dataType,
          source: variable.originalName,
          encodingHint: observedEncoding(variable),
        }]
      : []
  }).sort((left, right) => {
    const rank = { continuous: 0, ordinal: 1, binary: 2, nominal: 3 } as const
    return rank[left.dataType] - rank[right.dataType]
  })
  return [...scores, ...observed]
}
