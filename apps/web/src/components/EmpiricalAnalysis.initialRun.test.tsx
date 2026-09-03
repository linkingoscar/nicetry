import { render, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { DatasetVersion } from '../types'
import { EmpiricalAnalysis } from './EmpiricalAnalysis'

const mocks = vi.hoisted(() => ({
  onSelectRun: vi.fn(),
  showToast: vi.fn(),
}))

vi.mock('./empirical/useEmpiricalAnalysisState', () => ({
  useEmpiricalAnalysisState: () => ({
    analysisJob: undefined,
    onSelectRun: mocks.onSelectRun,
    showToast: mocks.showToast,
    toastText: null,
  }),
}))

vi.mock('./analyses/useEmpiricalAnalysisIndexSync', () => ({
  useEmpiricalAnalysisIndexSync: vi.fn(),
}))

vi.mock('./empirical/EmpiricalAnalysisShellHeader', () => ({
  EmpiricalAnalysisShellHeader: () => null,
}))

vi.mock('./empirical/EmpiricalResultsSection', () => ({
  EmpiricalResultsSection: () => null,
}))

const dataset = {
  id: 'dataset_demo',
  projectId: 'project_demo',
  originalFile: { name: 'survey.csv', sha256: 'a'.repeat(64) },
  dictionary: { version: 1 },
} as unknown as DatasetVersion

beforeEach(() => {
  mocks.onSelectRun.mockReset()
  mocks.showToast.mockReset()
  localStorage.clear()
})

describe('EmpiricalAnalysis requested run routing', () => {
  it('forwards an Output-selected run to the existing history restore path exactly once', async () => {
    const view = render(
      <EmpiricalAnalysis
        dataset={dataset}
        measurement={null}
        analysisId="analysis_demo"
        analysisProcedure="descriptives"
        initialRunId="run_selected"
      />,
    )

    await waitFor(() => expect(mocks.onSelectRun).toHaveBeenCalledWith('run_selected'))
    expect(mocks.onSelectRun).toHaveBeenCalledTimes(1)

    view.rerender(
      <EmpiricalAnalysis
        dataset={dataset}
        measurement={null}
        analysisId="analysis_demo"
        analysisProcedure="descriptives"
        initialRunId="run_selected"
      />,
    )
    expect(mocks.onSelectRun).toHaveBeenCalledTimes(1)
  })
})
