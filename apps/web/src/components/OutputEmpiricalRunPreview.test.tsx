import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getEmpiricalSegment } from '../api/empirical-analysis'
import type { EmpiricalAnalysisOptions } from '../types'
import { OutputEmpiricalRunPreview } from './OutputEmpiricalRunPreview'

vi.mock('../api/empirical-analysis', () => ({
  getEmpiricalSegment: vi.fn(),
}))
vi.mock('./empirical/EmpiricalOverviewTab', () => ({
  EmpiricalOverviewTab: () => <div>summary-preview</div>,
}))
vi.mock('./empirical/EmpiricalCorrelationTab', () => ({
  EmpiricalCorrelationTab: () => <div>correlation-preview</div>,
}))

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

const options = (procedure: EmpiricalAnalysisOptions['procedure']): EmpiricalAnalysisOptions => ({
  procedure,
  analysisVariableIds: [],
  constructIds: [],
  factorCount: 1,
  confidenceLevel: 0.95,
  correlationMethod: 'pearson',
  correlationPAdjust: 'BH',
  groupOmnibusPAdjust: 'holm',
  multiplicityPAdjust: 'BH',
  groupVariableId: null,
  aggregationVariableId: null,
  outcomeVariableId: null,
  predictorVariableIds: [],
  controlVariableIds: [],
  responseSurfacePredictorIds: [],
}) as EmpiricalAnalysisOptions

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(getEmpiricalSegment).mockResolvedValue({} as never)
})

describe('OutputEmpiricalRunPreview', () => {
  it('loads only the summary segment for descriptive-family runs', async () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_demo" measurementVersion={null} reportId="report_1" options={options('descriptives')} />,
      { wrapper },
    )

    expect(screen.getByText('summary-preview')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledWith('dataset_demo', null, 'report_1', 'summary'))
    expect(getEmpiricalSegment).toHaveBeenCalledTimes(1)
  })

  it('loads only the correlation segment for correlation runs', async () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_demo" measurementVersion={2} reportId="report_2" options={options('correlation')} />,
      { wrapper },
    )

    expect(screen.getByText('correlation-preview')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledWith('dataset_demo', 2, 'report_2', 'correlation'))
    expect(getEmpiricalSegment).toHaveBeenCalledTimes(1)
  })

  it('does not fetch a segment for methods not yet migrated into the Output preview', () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_demo" measurementVersion={null} reportId="report_3" options={options('regression')} />,
      { wrapper },
    )

    expect(screen.getByText(/完整只读结果预览仍在迁移中/)).toBeInTheDocument()
    expect(getEmpiricalSegment).not.toHaveBeenCalled()
  })
})
