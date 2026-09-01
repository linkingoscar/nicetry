import { useState } from 'react'
import type { ColumnLayoutMode } from '../../utils/figureExport'

export type JournalColorPreset = 'emerald' | 'amj' | 'psych' | 'monochrome'

export interface ColorScheme {
  label: string
  minus1sd: string
  mean: string
  plus1sd: string
  positive: string
  negative: string
  line: string
}

export const JOURNAL_COLOR_PRESETS: Record<JournalColorPreset, ColorScheme> = {
  emerald: {
    label: 'Academic Cobalt',
    minus1sd: '#dc2626',
    mean: '#475569',
    plus1sd: '#2563eb',
    positive: '#052796',
    negative: '#dc2626',
    line: '#052796',
  },
  amj: {
    label: 'AMJ Navy Blue',
    minus1sd: '#f59e0b',
    mean: '#0284c7',
    plus1sd: '#1e3a8a',
    positive: '#1e3a8a',
    negative: '#b91c1c',
    line: '#1e3a8a',
  },
  psych: {
    label: 'Psychology Classic',
    minus1sd: '#7e22ce',
    mean: '#0d2c94',
    plus1sd: '#991b1b',
    positive: '#0d2c94',
    negative: '#991b1b',
    line: '#991b1b',
  },
  monochrome: {
    label: '黑白双色 (Monochrome)',
    minus1sd: '#6b7280',
    mean: '#374151',
    plus1sd: '#000000',
    positive: '#000000',
    negative: '#4b5563',
    line: '#000000',
  },
}

interface JournalPresetSelectorProps {
  currentPreset: JournalColorPreset
  onPresetChange: (preset: JournalColorPreset) => void
  onExportSvg?: (mode?: ColumnLayoutMode) => void
  onExport300Dpi?: (mode?: ColumnLayoutMode) => void
}

export function JournalPresetSelector({
  currentPreset,
  onPresetChange,
  onExportSvg,
  onExport300Dpi,
}: JournalPresetSelectorProps) {
  const [isExporting, setIsExporting] = useState(false)

  const handleExport = (fn?: (mode?: ColumnLayoutMode) => void, mode?: ColumnLayoutMode) => {
    if (!fn || isExporting) return
    setIsExporting(true)
    fn(mode)
    setTimeout(() => setIsExporting(false), 600)
  }

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '8px',
        flexWrap: 'wrap',
        marginBottom: '12px',
        padding: '6px 10px',
        background: 'var(--bg-subtle)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600 }}>
          期刊 Preset:
        </span>
        {(Object.keys(JOURNAL_COLOR_PRESETS) as JournalColorPreset[]).map((preset) => {
          const isSelected = currentPreset === preset
          return (
            <button
              key={preset}
              type="button"
              style={{
                padding: '2px 8px',
                fontSize: '10px',
                borderRadius: '6px',
                border: `1px solid ${isSelected ? 'var(--brand-accent)' : 'var(--border-subtle)'}`,
                background: isSelected ? 'var(--bg-hover)' : 'var(--bg-surface)',
                color: isSelected ? 'var(--brand-primary)' : 'var(--text-body)',
                fontWeight: isSelected ? 700 : 500,
                cursor: 'pointer',
              }}
              onClick={() => onPresetChange(preset)}
            >
              {JOURNAL_COLOR_PRESETS[preset].label}
            </button>
          )
        })}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        {onExport300Dpi ? (
          <button
            type="button"
            className="btn-base"
            disabled={isExporting}
            style={{
              padding: '3px 9px',
              fontSize: '10px',
              fontWeight: 700,
              borderRadius: '6px',
              border: 0,
              background: 'var(--text-main)',
              color: '#ffffff',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              opacity: isExporting ? 0.7 : 1,
            }}
            onClick={() => handleExport(onExport300Dpi, 'standard')}
          >
            {isExporting ? '⏳ 导出中...' : '🖼️ 导出 300 DPI PNG'}
          </button>
        ) : null}

        {onExportSvg ? (
          <button
            type="button"
            className="btn-base"
            disabled={isExporting}
            style={{
              padding: '3px 9px',
              fontSize: '10px',
              fontWeight: 700,
              borderRadius: '6px',
              border: '1px solid var(--brand-primary)',
              background: 'var(--bg-surface)',
              color: 'var(--brand-primary)',
              cursor: isExporting ? 'not-allowed' : 'pointer',
              opacity: isExporting ? 0.7 : 1,
            }}
            onClick={() => handleExport(onExportSvg, 'standard')}
          >
            {isExporting ? '⏳ 导出中...' : '📐 导出 SVG 矢量图'}
          </button>
        ) : null}
      </div>
    </div>
  )
}
