import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { EmpiricalResultsNav } from './EmpiricalResultsNav'


describe('EmpiricalResultsNav', () => {
  it('uses accurate method labels and report-driven availability badges', () => {
    const onChange = vi.fn()
    render(
      <EmpiricalResultsNav
        activeTab="overview"
        pending={false}
        statusMap={{
          groups: 'not_requested',
          regression: 'available',
          advanced: 'warning',
          longitudinal: 'not_requested',
          diary: 'available',
        }}
        onChange={onChange}
      />,
    )

    expect(screen.queryByText(/PROCESS 中介\/调节/)).not.toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /分层回归.*有结果/ })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /组间与聚合.*未配置/ })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /高级与稳健性.*需关注/ })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /纵向面板.*未配置/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: /日记 \/ ESM.*有结果/ }))
    expect(onChange).toHaveBeenCalledWith('diary')
  })
})
