import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { ResearchStart } from './ResearchStart'

describe('ResearchStart', () => {
  it('uses import and analysis as the primary entry while keeping planning as a no-data tool', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<ResearchStart onSelect={onSelect} />)

    const analyze = screen.getByRole('button', { name: /导入数据并开始分析/ })
    const planning = screen.getByRole('button', { name: /功效与研究规划/ })
    expect(analyze).toBeInTheDocument()
    expect(planning).toBeInTheDocument()
    expect(screen.queryByText(/你现在处于哪个阶段/)).not.toBeInTheDocument()

    await user.click(analyze)
    expect(onSelect).toHaveBeenCalledWith('analyze')

    await user.click(planning)
    expect(onSelect).toHaveBeenCalledWith('plan')
  })
})
