import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import {
  ExperimentWizard,
  experimentAnalysisTypeForSlice,
  experimentDesignTypeForSlice,
  type ExperimentWizardSpec,
} from './ExperimentWizard'

vi.mock('./DatasetVariablePicker', () => ({
  DatasetVariablePicker: ({ label, onChange }: { label: string; onChange: (ids: string[]) => void }) => (
    <button type="button" onClick={() => onChange(['covariate_1'])}>{label}</button>
  ),
}))

const variables = [
  { id: 'outcome', name: 'outcome', label: 'Outcome', type: 'numeric' },
  { id: 'time_1', name: 'time_1', label: 'T1', type: 'numeric' },
  { id: 'time_2', name: 'time_2', label: 'T2', type: 'numeric' },
  { id: 'subject', name: 'subject', label: 'Subject', type: 'categorical' },
  { id: 'group', name: 'group', label: 'Group', type: 'categorical' },
  { id: 'cluster', name: 'cluster', label: 'Cluster', type: 'categorical' },
] as never[]

const baseSpec: ExperimentWizardSpec = {
  family: 'experimental_design',
  analysisType: 'anova',
  designType: 'factorial_anova',
  dataLayout: 'long',
  outcomeIds: ['outcome'],
  betweenFactors: [{ variableId: 'group', coding: 'sum' }],
  withinFactors: [],
  covariateIds: [],
  sumOfSquares: 'III',
  sphericityCorrection: 'auto',
  postHocAdjustment: 'holm',
  covariateCentering: 'grand_mean',
  homogeneityOfSlopes: 'check_and_warn',
}

describe('ExperimentWizard method-scoped forms', () => {
  it('maps registered slices to one locked design and analysis type', () => {
    expect(experimentDesignTypeForSlice('experimental_design.factorial_anova.long.single_outcome')).toBe('factorial_anova')
    expect(experimentDesignTypeForSlice('experimental_design.ancova.long.single_outcome')).toBe('ancova')
    expect(experimentDesignTypeForSlice('experimental_design.repeated_measures.single_within')).toBe('repeated_measures')
    expect(experimentDesignTypeForSlice('experimental_design.mixed_design.single_within')).toBe('mixed_design')
    expect(experimentDesignTypeForSlice('experimental_design.glm_cluster.long.single_outcome')).toBe('factorial_anova')
    expect(experimentAnalysisTypeForSlice('experimental_design.glm_cluster.long.single_outcome')).toBe('glm_cluster')
  })

  it('uses the backend covariateIds field for ANCOVA and exposes only supported adjustments', () => {
    const onChange = vi.fn()
    render(
      <ExperimentWizard
        spec={{ ...baseSpec, designType: 'factorial_anova' }}
        onChange={onChange}
        variables={variables}
        sliceId="experimental_design.ancova.long.single_outcome"
      />,
    )

    expect(screen.getByRole('heading', { name: '组间协方差分析（ANCOVA）' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /控制协变量/ }))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ covariateIds: ['covariate_1'] }))
    expect(screen.queryByText(/Bonferroni/i)).not.toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Benjamini–Hochberg' })).toBeInTheDocument()
  })

  it('shows repeated-measures identity, within-factor and sphericity settings', () => {
    render(
      <ExperimentWizard
        spec={{
          ...baseSpec,
          designType: 'factorial_anova',
          betweenFactors: [],
          subjectId: 'subject',
          withinFactors: [{ id: 'time', name: '时间', levels: ['T1', 'T2'], columns: {} }],
        }}
        onChange={vi.fn()}
        variables={variables}
        sliceId="experimental_design.repeated_measures.single_within"
      />,
    )

    expect(screen.getByRole('heading', { name: '重复测量分析' })).toBeInTheDocument()
    expect(screen.getByLabelText('被试 ID')).toBeInTheDocument()
    expect(screen.getByLabelText('数据布局')).toBeInTheDocument()
    expect(screen.getByLabelText('组内因子名称')).toBeInTheDocument()
    expect(screen.getByLabelText('球形性校正')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /组间处理/ })).not.toBeInTheDocument()
  })

  it('renders explicit cluster identity and the fixed CR0 boundary for cluster-robust GLM', () => {
    const onChange = vi.fn()
    render(
      <ExperimentWizard
        spec={{ ...baseSpec, analysisType: 'anova', clusterVariableId: null }}
        onChange={onChange}
        variables={variables}
        sliceId="experimental_design.glm_cluster.long.single_outcome"
      />,
    )

    expect(screen.getByRole('heading', { name: 'Cluster-robust Gaussian GLM' })).toBeInTheDocument()
    expect(screen.getByLabelText('Cluster ID')).toBeInTheDocument()
    expect(screen.getByLabelText('聚类稳健标准误')).toHaveValue('CR0')
    fireEvent.change(screen.getByLabelText('Cluster ID'), { target: { value: 'cluster' } })
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ analysisType: 'glm_cluster', clusterVariableId: 'cluster', clusterSE: 'CR0' }))
  })
})
