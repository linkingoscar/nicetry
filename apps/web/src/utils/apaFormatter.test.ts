import { describe, expect, it } from 'vitest'
import {
  formatAPAConfidenceInterval,
  formatAPAPValue,
  formatAPASigStars,
  formatAPAStat,
} from './apaFormatter'

describe('apaFormatter', () => {

  it('omits leading zero for statistics less than 1', () => {
    expect(formatAPAStat(0.456)).toBe('.456')
    expect(formatAPAStat(-0.321)).toBe('-.321')
    expect(formatAPAStat(0)).toBe('.000')
    expect(formatAPAStat(1.25)).toBe('1.250')
    expect(formatAPAStat(null)).toBe('—')
    expect(formatAPAStat(NaN)).toBe('—')
  })

  it('formats p-values according to APA 7th', () => {
    expect(formatAPAPValue(0.0004)).toBe('< .001')
    expect(formatAPAPValue(0.042)).toBe('.042')
    expect(formatAPAPValue(0.500)).toBe('.500')
    expect(formatAPAPValue(null)).toBe('—')
  })

  it('returns significance stars', () => {
    expect(formatAPASigStars(0.0001)).toBe('***')
    expect(formatAPASigStars(0.005)).toBe('**')
    expect(formatAPASigStars(0.03)).toBe('*')
    expect(formatAPASigStars(0.12)).toBe(' (ns)')
    expect(formatAPASigStars(null)).toBe('')
  })

  it('formats confidence intervals', () => {
    expect(formatAPAConfidenceInterval(0.123, 0.456)).toBe('95% CI [.123, .456]')
    expect(formatAPAConfidenceInterval(-0.05, 0.25, 2, 0.90)).toBe('90% CI [-.05, .25]')
    expect(formatAPAConfidenceInterval(null, 0.5)).toBe('—')
  })
})
