import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CommandPalette } from './CommandPalette'

describe('CommandPalette', () => {
  it('renders commands when isOpen is true', () => {
    const onSelectView = vi.fn()
    const onClose = vi.fn()

    render(<CommandPalette isOpen={true} onClose={onClose} onSelectView={onSelectView} />)

    expect(screen.getByPlaceholderText(/搜索工作区/i)).toBeInTheDocument()
    expect(screen.getByText(/跳转: 数据与测量/i)).toBeInTheDocument()
  })

  it('filters commands on query input and selects item on click', () => {
    const onSelectView = vi.fn()
    const onClose = vi.fn()

    render(<CommandPalette isOpen={true} onClose={onClose} onSelectView={onSelectView} />)

    const input = screen.getByPlaceholderText(/搜索工作区/i)
    fireEvent.change(input, { target: { value: 'PROCESS' } })

    const item = screen.getByText(/跳转: 模型画布 PROCESS/i)
    expect(item).toBeInTheDocument()

    fireEvent.click(item)
    expect(onSelectView).toHaveBeenCalledWith('model')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('opens the restored advanced methods workspace', () => {
    const onSelectView = vi.fn()
    const onClose = vi.fn()

    render(<CommandPalette isOpen={true} onClose={onClose} onSelectView={onSelectView} />)

    fireEvent.click(screen.getByText(/跳转: 当前数据的专属方法/))
    expect(onSelectView).toHaveBeenCalledWith('methods')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('routes longitudinal and diary commands to their dedicated empirical tabs', () => {
    const onSelectView = vi.fn()
    const onSelectEmpiricalTab = vi.fn()
    const onClose = vi.fn()

    render(
      <CommandPalette
        isOpen={true}
        onClose={onClose}
        onSelectView={onSelectView}
        onSelectEmpiricalTab={onSelectEmpiricalTab}
      />,
    )

    fireEvent.click(screen.getByText(/实证分区: 7. 纵向面板/))
    expect(onSelectView).toHaveBeenCalledWith('empirical')
    expect(onSelectEmpiricalTab).toHaveBeenCalledWith('longitudinal')

    fireEvent.click(screen.getByText(/实证分区: 8. 日记 \/ ESM/))
    expect(onSelectEmpiricalTab).toHaveBeenCalledWith('diary')
  })
})
