import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ResearchStart } from './ResearchStart'

describe('ResearchStart', () => {
  it('separates planning from analysis as the first decision', async () => {
    const onSelect = vi.fn()
    render(<ResearchStart onSelect={onSelect} />)

    expect(screen.getByRole('button', { name: /规划新研究/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /分析已有数据/ })).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /分析已有数据/ }))
    expect(onSelect).toHaveBeenCalledWith('analyze')
  })
})
