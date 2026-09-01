import { useState } from 'react'

interface AcademicInterpretationProps {
  text: string
  onCopySuccess?: () => void
}

export type JournalStyle = 'psych' | 'amj' | 'manag'

function linesWithStableKeys(text: string) {
  const occurrences = new Map<string, number>()
  return text.split('\n').map((line) => {
    const occurrence = (occurrences.get(line) ?? 0) + 1
    occurrences.set(line, occurrence)
    return { key: `${line}\u0000${occurrence}`, line }
  })
}

/**
 * Transforms plain academic interpretation into target journal style template.
 */
function adaptTextToJournalStyle(text: string, style: JournalStyle): string {
  if (style === 'psych') {
    return text.replace(
      /根据 Preacher & Hayes \(\d{4}\) 提出的 Bootstrap 中介检验方法/g,
      '遵循 Preacher & Hayes (2008) 推荐的非参数 Percentile Bootstrap 检验方法（重复抽样 5,000 次）',
    )
  }
  if (style === 'amj') {
    return `[APA 7th English Journal Style (AMJ/JAP Standard)]\nTo examine the hypothesized structural model and measurement invariance across sub-groups, we followed established empirical guidelines (Cheung & Rensvold, 2002; Hamaker et al., 2015). Empirical estimates and 95% confidence intervals were generated as follows:\n\n${text
      .replace(/中介效应显著/g, 'the indirect effect reached statistical significance')
      .replace(/直接效应/g, 'direct effect')
      .replace(/间接效应/g, 'indirect effect')
      .replace(/置信区间/g, '95% Boot CI')
      .replace(/等值成立/g, 'measurement invariance held')}`
  }
  if (style === 'manag') {
    return `【管理世界 / 中国管理科学期刊写作规范】\n针对多时点纵向与多群组数据结构，本研究遵循随机截距交叉滞后 (RI-CLPM) 与多群组 SEM 范式，分离个体间固定特质与个体内动态衍生变异（Hamaker et al., 2015）：\n\n${text}`
  }
  return text
}

export function AcademicInterpretation({ text, onCopySuccess }: AcademicInterpretationProps) {
  const [selectedStyle, setSelectedStyle] = useState<JournalStyle>('psych')
  const [copied, setCopied] = useState(false)

  const adaptedText = adaptTextToJournalStyle(text, selectedStyle)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(adaptedText)
      setCopied(true)
      if (onCopySuccess) onCopySuccess()
      setTimeout(() => setCopied(false), 2500)
    } catch (err) {
      console.error('Failed to copy interpretation paragraph:', err)
    }
  }

  return (
    <div className="interpretation-container" style={{ display: 'grid', gap: '12px', marginTop: '12px' }}>
      {/* Journal Template Style Switcher Toolbar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          flexWrap: 'wrap',
          background: '#ffffff',
          padding: '8px 12px',
          borderRadius: '8px',
          border: '1px solid #c7cbd9',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '11px', color: '#595d6b', fontWeight: 600 }}>
            期刊写作风格:
          </span>
          <button
            type="button"
            style={{
              padding: '3px 9px',
              fontSize: '11px',
              borderRadius: '6px',
              border: `1px solid ${selectedStyle === 'psych' ? '#1f2d5a' : '#cbd5e1'}`,
              background: selectedStyle === 'psych' ? '#e3e6f0' : '#ffffff',
              color: selectedStyle === 'psych' ? '#1f2d5a' : '#475569',
              fontWeight: selectedStyle === 'psych' ? 700 : 500,
              cursor: 'pointer',
            }}
            onClick={() => setSelectedStyle('psych')}
          >
            心理学报风格
          </button>
          <button
            type="button"
            style={{
              padding: '3px 9px',
              fontSize: '11px',
              borderRadius: '6px',
              border: `1px solid ${selectedStyle === 'amj' ? '#1f2d5a' : '#cbd5e1'}`,
              background: selectedStyle === 'amj' ? '#e3e6f0' : '#ffffff',
              color: selectedStyle === 'amj' ? '#1f2d5a' : '#475569',
              fontWeight: selectedStyle === 'amj' ? 700 : 500,
              cursor: 'pointer',
            }}
            onClick={() => setSelectedStyle('amj')}
          >
            AMJ / JAP (英文 APA 7th)
          </button>
          <button
            type="button"
            style={{
              padding: '3px 9px',
              fontSize: '11px',
              borderRadius: '6px',
              border: `1px solid ${selectedStyle === 'manag' ? '#1f2d5a' : '#cbd5e1'}`,
              background: selectedStyle === 'manag' ? '#e3e6f0' : '#ffffff',
              color: selectedStyle === 'manag' ? '#1f2d5a' : '#475569',
              fontWeight: selectedStyle === 'manag' ? 700 : 500,
              cursor: 'pointer',
            }}
            onClick={() => setSelectedStyle('manag')}
          >
            管理世界风格
          </button>
        </div>

        <button
          type="button"
          style={{
            padding: '4px 12px',
            fontSize: '11px',
            borderRadius: '6px',
            border: 0,
            background: copied ? '#152e80' : '#1f2d5a',
            color: '#ffffff',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(31, 45, 90, 0.2)',
          }}
          onClick={handleCopy}
        >
          {copied ? '✓ 已复制论文段落' : '📋 一键复制标准论文段落'}
        </button>
      </div>

      {/* Rendered Academic Paragraph */}
      <div
        className="interpretation-content"
        style={{ fontSize: '13px', lineHeight: '1.65', color: '#2b2f3a', background: '#f8f8fa', padding: '14px', borderRadius: '8px', border: '1px solid #e2e3e8' }}
      >
        {linesWithStableKeys(adaptedText).map(({ key, line }) => {
          if (line.startsWith('### ')) {
            return <h4 key={key} style={{ color: '#1f2d5a', marginTop: '14px', marginBottom: '6px' }}>{line.slice(4)}</h4>
          }
          if (line.startsWith('## ')) {
            return <h3 key={key} style={{ color: '#1f2d5a', marginTop: '18px', marginBottom: '6px' }}>{line.slice(3)}</h3>
          }
          if (line.startsWith('- ')) {
            return <li key={key} style={{ marginLeft: '16px', listStyleType: 'disc' }}>{line.slice(2)}</li>
          }
          return <p key={key} style={{ margin: '0 0 6px' }}>{line}</p>
        })}
      </div>
    </div>
  )
}
