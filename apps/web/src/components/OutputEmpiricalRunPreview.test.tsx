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
vi.mock('./empirical/EmpiricalProcedureResult', () => ({
  EmpiricalProcedureResultView: ({ reportOptions }: { reportOptions: EmpiricalAnalysisOptions }) => (
    <div>procedure-preview:{reportOptions.procedure}</div>
  ),
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

    expect(screen.getByText('procedure-preview:descriptives')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledWith('dataset_demo', null, 'report_1', 'summary'))
    expect(getEmpiricalSegment).toHaveBeenCalledTimes(1)
  })

  it('loads only the correlation segment for correlation runs', async () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_demo" measurementVersion={2} reportId="report_2" options={options('correlation')} />,
      { wrapper },
    )

    expect(screen.getByText('procedure-preview:correlation')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledWith('dataset_demo', 2, 'report_2', 'correlation'))
    expect(getEmpiricalSegment).toHaveBeenCalledTimes(1)
  })

  it('loads the regression result segment for regression-family methods', async () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_demo" measurementVersion={null} reportId="report_3" options={options('regression')} />,
      { wrapper },
    )

    expect(screen.getByText('procedure-preview:regression')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledWith('dataset_demo', null, 'report_3', 'regression'))
    expect(getEmpiricalSegment).toHaveBeenCalledTimes(1)
  })

  it('loads the dependent summary, measurement, and validity segments for validity', async () => {
    render(
      <OutputEmpiricalRunPreview datasetId="dataset_old" measurementVersion={4} reportId="report_4" options={options('validity')} />,
      { wrapper },
    )

    expect(screen.getByText('procedure-preview:validity')).toBeInTheDocument()
    await waitFor(() => expect(getEmpiricalSegment).toHaveBeenCalledTimes(3))
    expect(vi.mocked(getEmpiricalSegment).mock.calls.map((call) => call[3]).sort()).toEqual([
      'efa_cfa',
      'summary',
      'validity',
    ])
  })
})
