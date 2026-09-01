import { describe, expect, it, vi } from 'vitest'
import { openAPAManuscriptReport } from './generateFullAPAReport'

describe('generateFullAPAReport', () => {
  it('opens a new window and writes HTML APA manuscript', () => {
    const mockWrite = vi.fn()
    const mockClose = vi.fn()
    const mockWindow = {
      document: {
        write: mockWrite,
        close: mockClose,
      },
    }

    vi.spyOn(window, 'open').mockReturnValue(mockWindow as unknown as Window)

    openAPAManuscriptReport({
      reportId: 'rep_123',
      datasetName: 'test.csv',
      sampleCount: 300,
      kmo: 0.85,
      harmanFirstFactor: 32.5,
    })

    expect(window.open).toHaveBeenCalledWith('', '_blank')
    expect(mockWrite).toHaveBeenCalledOnce()
    const writtenHtml = mockWrite.mock.calls[0][0] as string
    expect(writtenHtml).toContain('APA 7th Standard Manuscript')
    expect(writtenHtml).toContain('Harman\'s Single-Factor Test')
    expect(mockClose).toHaveBeenCalledOnce()
  })

  it('escapes user-controlled strings before writing HTML', () => {
    const mockWrite = vi.fn()
    const mockWindow = {
      document: {
        write: mockWrite,
        close: vi.fn(),
      },
    }

    vi.spyOn(window, 'open').mockReturnValue(mockWindow as unknown as Window)

    openAPAManuscriptReport({
      reportId: 'rep_123',
      datasetName: '<img src=x onerror=alert(1)>',
      descriptives: [{ label: '<script>steal()</script>', n: 1, missing: 0, mean: 1, sd: 0, minimum: 1, maximum: 1, skewness: 0, kurtosis: 0 }],
      correlationTable: {
        variables: [{ id: 'v', label: '"><svg onload=alert(2)>' }],
        coefficients: [[1]],
      },
      academicInterpretation: '<b>结论</b>\n第二行',
    })

    const writtenHtml = mockWrite.mock.calls[0][0] as string
    expect(writtenHtml).not.toContain('<img src=x')
    expect(writtenHtml).not.toContain('<script>steal')
    expect(writtenHtml).not.toContain('<svg onload')
    expect(writtenHtml).toContain('&lt;img src=x onerror=alert(1)&gt;')
    expect(writtenHtml).toContain('&lt;script&gt;steal()&lt;/script&gt;')
    expect(writtenHtml).toContain('&lt;b&gt;结论&lt;/b&gt;<br/>第二行')
  })

  it('does not fabricate an affirmative conclusion when interpretation is missing', () => {
    const mockWrite = vi.fn()
    const mockWindow = {
      document: {
        write: mockWrite,
        close: vi.fn(),
      },
    }

    vi.spyOn(window, 'open').mockReturnValue(mockWindow as unknown as Window)

    openAPAManuscriptReport({ reportId: 'rep_no_interpretation' })

    const writtenHtml = mockWrite.mock.calls[0][0] as string
    expect(writtenHtml).toContain('需人工撰写解释')
    expect(writtenHtml).not.toContain('模型假定成立')
    expect(writtenHtml).not.toContain('Preacher & Hayes (2008)')
  })
})
