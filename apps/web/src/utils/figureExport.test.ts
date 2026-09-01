import { describe, expect, it, vi } from 'vitest'
import { exportSvgAsFile } from './figureExport'

describe('figureExport', () => {
  it('clones SVG element and triggers download', () => {
    const mockSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    mockSvg.setAttribute('width', '500')
    mockSvg.setAttribute('height', '300')

    const createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test')
    const revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {})

    exportSvgAsFile(mockSvg, 'test_plot.svg')

    expect(createObjectURLSpy).toHaveBeenCalledOnce()
    expect(revokeObjectURLSpy).toHaveBeenCalledOnce()
  })
})
