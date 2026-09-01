import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VisualCIBar, renderSigBadge } from './EmpiricalBadges'

describe('VisualCIBar', () => {
  it('labels the requested confidence level instead of hardcoding 95%', () => {
    render(<VisualCIBar lower={0.1} upper={0.2} confidenceLevel={0.9} />)
    const bar = screen.getByText(/90%/i)
    expect(bar).toBeInTheDocument()
    expect(bar.closest('span')).toHaveAttribute('title', expect.stringContaining('90% 置信区间'))
  })

  it('falls back to 95% only when no level is supplied', () => {
    render(<VisualCIBar lower={-0.1} upper={0.1} confidenceLevel={null} />)
    expect(screen.getByText(/95%/i)).toBeInTheDocument()
  })
})

describe('renderSigBadge', () => {
  it('uses the multiplicity-adjusted p value passed by callers', () => {
    expect(renderSigBadge(0.04)?.props.title).toBe('p < 0.05')
    expect(renderSigBadge(0.06)).toBeNull()
  })
})
