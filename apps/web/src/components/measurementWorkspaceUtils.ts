import type {
  ConstructDraft,
  MeasurementVersion,
} from '../types'

export function newConstruct(sequence: number): ConstructDraft {
  return {
    id: `construct_${sequence}`,
    name: '',
    itemIds: [],
    reverseItemIds: [],
    theoreticalMinimum: 1,
    theoreticalMaximum: 5,
    aggregation: 'mean',
    minimumValidProportion: 0.8,
  }
}

export function formatMetric(value: number | null, digits = 3): string {
  return value === null ? '—' : value.toFixed(digits)
}

export function formatPercent(value: number | null): string {
  return value === null ? '—' : `${(value * 100).toFixed(1)}%`
}

export function draftsFromMeasurement(measurement?: MeasurementVersion): ConstructDraft[] {
  if (!measurement) return [newConstruct(1)]
  return measurement.constructs.map((construct) => ({
    id: construct.id,
    name: construct.name,
    itemIds: [...construct.itemIds],
    reverseItemIds: [...construct.reverseItemIds],
    theoreticalMinimum: construct.theoreticalMinimum,
    theoreticalMaximum: construct.theoreticalMaximum,
    aggregation: construct.aggregation,
    minimumValidProportion: construct.minimumValidProportion,
  }))
}
