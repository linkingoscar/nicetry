import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { AdvancedAnalysisCapability } from '../../types'
import { AnalysisWizard } from './AnalysisWizard'

vi.mock('./WizardConfigStep', () => ({
  WizardConfigStep: ({ presentation }: { presentation?: string }) => <div>config:{presentation}</div>,
}))
vi.mock('./WizardStatusCard', () => ({
  WizardStatusCard: ({ presentation }: { presentation?: string }) => <div>status:{presentation}</div>,
}))

function capability(sliceId: string): AdvancedAnalysisCapability {
  return {
    family: 'experimental_design',
    sliceId,
    label: '测试方法',
    status: 'experimental',
    executionAvailable: true,
    specVersion: '0.1.0',
    resultVersion: '0.1.0',
    plannedEngine: 'R',
    minimumValidation: [],
    slices: [],
  } as AdvancedAnalysisCapability
}

describe('AnalysisWizard presentation', () => {
  it('uses the normal analysis shell for promoted high-frequency forms', () => {
    render(
      <AnalysisWizard
        capability={capability('experimental_design.factorial_anova.long.single_outcome')}
        datasetId="dataset_demo"
        onJobStarted={vi.fn()}
      />,
    )

    expect(screen.getByText('config:standard')).toBeInTheDocument()
    expect(screen.queryByRole('navigation', { name: '向导步骤' })).not.toBeInTheDocument()
  })

  it('keeps specialist advanced slices in the original wizard shell', () => {
    render(
      <AnalysisWizard
        capability={capability('experimental_design.glm_cluster.long.single_outcome')}
        datasetId="dataset_demo"
        onJobStarted={vi.fn()}
      />,
    )

    expect(screen.getByText('config:advanced')).toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: '向导步骤' })).toBeInTheDocument()
  })
})
