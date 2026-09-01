import type { DatasetVariableItem } from './DatasetVariablePicker'
import type { ResolvedAnalysisContext } from '../../types/analysis-context'

export interface AnalysisSpecBuilderContext {
  base: Record<string, unknown>
  sliceId: string | undefined
  datasetId: string | undefined
  variables: DatasetVariableItem[]
  numericIds: string[]
  categoricalIds: string[]
  selectedItemIds: string[]
  selectedConstructs: Array<{ id: string; label: string; itemIds: string[] }>
  context?: ResolvedAnalysisContext | null
  template: (spec: object) => object
}
