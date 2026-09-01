import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { DEFAULT_STUDY_CONTEXT, type StudyContext } from '../../types/study-context'
import { StudyContextSwitcher } from './StudyContextSwitcher'

const context: StudyContext = {
  schemaVersion: '1.0.0',
  timeStructure: 'cross_sectional',
  dependenceStructure: 'independent',
  design: 'quasi_experimental',
}

describe('StudyContextSwitcher', () => {
  it('explicitly confirms unchanged defaults and offers retry without toggling radios', async () => {
    const onChange = vi.fn()
    const view = render(<StudyContextSwitcher value={DEFAULT_STUDY_CONTEXT} hasDataset persistence="unconfirmed" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: '确认并保存研究结构' }))
    expect(onChange).toHaveBeenCalledWith(DEFAULT_STUDY_CONTEXT)
    view.rerender(<StudyContextSwitcher value={DEFAULT_STUDY_CONTEXT} hasDataset persistence="error" onChange={onChange} />)
    await userEvent.click(screen.getByRole('button', { name: '重试保存研究结构' }))
    expect(onChange).toHaveBeenCalledTimes(2)
  })
  it('keeps imported context compact and allows editing without losing its selected values', async () => {
    const onChange = vi.fn()
    render(<StudyContextSwitcher value={context} hasDataset onChange={onChange} />)
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: '修改研究结构' }))
    expect(screen.getByRole('radio', { name: /非随机比较/ })).toBeChecked()
    await userEvent.click(screen.getByRole('radio', { name: /追踪面板/ }))
    expect(onChange).toHaveBeenCalledWith({ ...context, timeStructure: 'panel' })
    await userEvent.click(screen.getByRole('button', { name: '收起研究结构' }))
    expect(screen.queryByRole('radio')).not.toBeInTheDocument()
  })
  it('treats temporal, dependence and design structures as independent choices', async () => {
    const onChange = vi.fn()
    const { rerender } = render(
      <StudyContextSwitcher value={DEFAULT_STUDY_CONTEXT} hasDataset={false} onChange={onChange} />,
    )

    await userEvent.click(screen.getByRole('radio', { name: /存在聚类/ }))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      timeStructure: 'cross_sectional',
      dependenceStructure: 'nested',
      design: 'observational',
    }))

    rerender(
      <StudyContextSwitcher
        value={{ ...DEFAULT_STUDY_CONTEXT, dependenceStructure: 'nested' }}
        hasDataset
        onChange={onChange}
      />,
    )
    expect(screen.getByText(/必须指定 cluster ID/)).toBeInTheDocument()
  })

  it('explains the assignment mechanism for each study design', () => {
    render(
      <StudyContextSwitcher value={DEFAULT_STUDY_CONTEXT} hasDataset={false} onChange={vi.fn()} />,
    )

    expect(screen.getByText(/不随机分配处理，只观察已有差异/)).toBeInTheDocument()
    expect(screen.getByText(/随机分配处理组 \/ 对照组/)).toBeInTheDocument()
    expect(screen.getByText(/当前不提供准实验因果识别、DiD、IV、RDD 或 IPW/)).toBeInTheDocument()
  })

  it('keeps historical nonrandom-comparison context without advertising a causal suite', () => {
    render(<StudyContextSwitcher value={context} hasDataset={false} onChange={vi.fn()} />)

    expect(screen.getByText('非随机比较')).toBeInTheDocument()
    expect(screen.getByText(/当前不提供准实验因果识别、DiD、IV、RDD 或 IPW/)).toBeInTheDocument()
    expect(screen.queryByText('准实验')).not.toBeInTheDocument()
  })
})
