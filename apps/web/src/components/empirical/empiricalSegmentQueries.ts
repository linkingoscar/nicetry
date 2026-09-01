import { useQuery } from '@tanstack/react-query'
import { getEmpiricalSegment } from '../../api'
import type {
  DatasetVersion,
  MeasurementVersion,
} from '../../types'
import type { EmpiricalResultTab } from './EmpiricalResultsNav'

export function useEmpiricalSegmentQueries(
  dataset: DatasetVersion,
  measurement: MeasurementVersion | null,
  reportId: string | undefined,
  activeTab: EmpiricalResultTab,
) {
  const keyBase = [dataset.id, (measurement?.version ?? null), reportId] as const
  return {
    summaryQuery: useQuery({
      queryKey: [...keyBase, 'summary'],
      queryFn: () => getEmpiricalSegment(dataset.id, (measurement?.version ?? null), reportId ?? '', 'summary'),
      enabled: !!reportId,
      staleTime: Infinity,
    }),
    correlationQuery: useQuery({
      queryKey: [...keyBase, 'correlation'],
      queryFn: () => getEmpiricalSegment(dataset.id, (measurement?.version ?? null), reportId ?? '', 'correlation'),
      enabled: !!reportId && activeTab === 'correlation',
      staleTime: Infinity,
    }),
    efaCfaQuery: useQuery({
      queryKey: [...keyBase, 'efa_cfa'],
      queryFn: () => getEmpiricalSegment(dataset.id, (measurement?.version ?? null), reportId ?? '', 'efa_cfa'),
      enabled: !!reportId && activeTab === 'measurement',
      staleTime: Infinity,
    }),
    validityQuery: useQuery({
      queryKey: [...keyBase, 'validity'],
      queryFn: () => getEmpiricalSegment(dataset.id, (measurement?.version ?? null), reportId ?? '', 'validity'),
      enabled: !!reportId && activeTab === 'measurement',
      staleTime: Infinity,
    }),
    regressionQuery: useQuery({
      queryKey: [...keyBase, 'regression'],
      queryFn: () => getEmpiricalSegment(dataset.id, (measurement?.version ?? null), reportId ?? '', 'regression'),
      enabled: !!reportId && ['groups', 'regression', 'advanced'].includes(activeTab),
      staleTime: Infinity,
    }),
  }
}
