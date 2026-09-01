/**
 * Utilities for exporting publication-grade SVG vector files and 300 DPI high-res PNG images.
 * Supports Nature/Science/IEEE Single Column (85mm / 3.35 in) and Double Column (175mm / 6.9 in) print modes.
 */

export type ColumnLayoutMode = 'standard' | 'single_column_85mm' | 'double_column_175mm'

export function exportSvgAsFile(
  svgElement: SVGSVGElement,
  filename = 'figure_export.svg',
  layoutMode: ColumnLayoutMode = 'standard'
) {
  const clone = svgElement.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')

  // Boost font size for Single Column (85mm) so text remains readable when printed at 85mm width
  const fontBoost = layoutMode === 'single_column_85mm' ? 'font-size: 13px !important;' : ''

  const styleElement = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  styleElement.textContent = `
    text { font-family: 'Times New Roman', Arial, sans-serif; ${fontBoost} }
    line, path, rect { shape-rendering: crispEdges; }
  `
  clone.insertBefore(styleElement, clone.firstChild)

  const svgString = new XMLSerializer().serializeToString(clone)
  const blob = new Blob([`<?xml version="1.0" encoding="UTF-8"?>\n${svgString}`], {
    type: 'image/svg+xml;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)

  const downloadLink = document.createElement('a')
  downloadLink.href = url
  downloadLink.download = filename
  document.body.appendChild(downloadLink)
  downloadLink.click()
  document.body.removeChild(downloadLink)
  URL.revokeObjectURL(url)
}
export function exportSvgAs300DpiPng(
  svgElement: SVGSVGElement,
  filename = 'figure_300dpi.png',
  layoutMode: ColumnLayoutMode = 'standard',
  dpiScale = 3.125,
) {
  const clone = svgElement.cloneNode(true) as SVGSVGElement
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg')

  // Single Column 85mm at 300 DPI = ~1004px width; Double Column 175mm = ~2067px width
  const targetWidth = layoutMode === 'single_column_85mm'
    ? 1004
    : layoutMode === 'double_column_175mm'
    ? 2067
    : 0

  const originalWidth = svgElement.viewBox.baseVal?.width || svgElement.clientWidth || 560
  const originalHeight = svgElement.viewBox.baseVal?.height || svgElement.clientHeight || 280

  const scaledWidth = targetWidth > 0 ? targetWidth : Math.round(originalWidth * dpiScale)
  const scaledHeight = Math.round(originalHeight * (scaledWidth / originalWidth))

  const fontBoost = layoutMode === 'single_column_85mm' ? 'font-size: 14px !important;' : ''
  const styleElement = document.createElementNS('http://www.w3.org/2000/svg', 'style')
  styleElement.textContent = `
    text { font-family: 'Times New Roman', Arial, sans-serif; ${fontBoost} }
  `
  clone.insertBefore(styleElement, clone.firstChild)

  const svgString = new XMLSerializer().serializeToString(clone)
  const svgBlob = new Blob([svgString], { type: 'image/svg+xml;charset=utf-8' })
  const url = URL.createObjectURL(svgBlob)

  const img = new Image()
  img.onload = () => {
    const canvas = document.createElement('canvas')
    canvas.width = scaledWidth
    canvas.height = scaledHeight
    const ctx = canvas.getContext('2d')
    if (ctx) {
      // White background for publication figure
      ctx.fillStyle = '#ffffff'
      ctx.fillRect(0, 0, scaledWidth, scaledHeight)
      ctx.drawImage(img, 0, 0, scaledWidth, scaledHeight)

      canvas.toBlob((blob) => {
        if (blob) {
          const pngUrl = URL.createObjectURL(blob)
          const downloadLink = document.createElement('a')
          downloadLink.href = pngUrl
          downloadLink.download = filename
          document.body.appendChild(downloadLink)
          downloadLink.click()
          document.body.removeChild(downloadLink)
          URL.revokeObjectURL(pngUrl)
        }
      }, 'image/png')
    }
    URL.revokeObjectURL(url)
  }
  img.src = url
}
