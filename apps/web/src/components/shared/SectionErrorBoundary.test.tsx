import { fireEvent, render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { SectionErrorBoundary } from './SectionErrorBoundary'

function BrokenSection(): ReactNode {
  throw new Error('broken result payload')
}

describe('SectionErrorBoundary', () => {
  it('contains a result rendering failure and can reset when the tab changes', () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const { rerender } = render(
      <SectionErrorBoundary resetKey="summary">
        <BrokenSection />
      </SectionErrorBoundary>,
    )

    expect(screen.getByRole('alert')).toHaveTextContent('本结果区暂时无法显示')
    fireEvent.click(screen.getByText('查看技术信息'))
    expect(screen.getByText('broken result payload')).toBeInTheDocument()

    rerender(
      <SectionErrorBoundary resetKey="correlation">
        <p>相关结果正常</p>
      </SectionErrorBoundary>,
    )
    expect(screen.getByText('相关结果正常')).toBeInTheDocument()
    consoleError.mockRestore()
  })
})
