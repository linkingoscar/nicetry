import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { CommandPalette } from './CommandPalette'

describe('CommandPalette', () => {
  it('renders the three primary workspace commands when open', () => {
    const onSelectView = vi.fn()
    const onClose = vi.fn()

    render(<CommandPalette isOpen={true} onClose={onClose} onSelectView={onSelectView} />)

    expect(screen.getByPlaceholderText(/搜索数据、分析、输出/i)).toBeInTheDocument()
    expect(screen.getByText(/跳转: 数据/i)).toBeInTheDocument()
    expect(screen.getByText(/跳转: 分析/i)).toBeInTheDocument()
    expect(screen.getByText(/跳转: 输出/i)).toBeInTheDocument()
  })

  it('routes model-oriented searches through the unified analysis workspace', () => {
    const onSelectView = vi.fn()
    const onClose = vi.fn()

    render(<CommandPalette isOpen={true} onClose={onClose} onSelectView={onSelectView} />)

    const input = screen.getByPlaceholderText(/搜索数据、分析、输出/i)
    fireEvent.change(input, { target: { value: 'SEM' } })

    const item = screen.getByText(/分析: 高阶 SEM/i)
    fireEvent.click(item)
    expect(onSelectView).toHaveBeenCalledWith('analyze')
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('routes longitudinal and diary commands through analysis while preserving empirical tab intent', () => {
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

    fireEvent.click(screen.getByText(/分析: 纵向面板/))
    expect(onSelectView).toHaveBeenCalledWith('analyze')
    expect(onSelectEmpiricalTab).toHaveBeenCalledWith('longitudinal')

    fireEvent.click(screen.getByText(/分析: 日记 \/ ESM/))
    expect(onSelectEmpiricalTab).toHaveBeenCalledWith('diary')
  })
})
