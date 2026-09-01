import { useEffect, useRef, useState, useMemo } from 'react'
import type { EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'
import { SearchIcon } from './Icons'
import type { CommandItem } from './CommandPalette.commands'
import { buildCommandPaletteCommands } from './CommandPalette.commands'
import styles from './CommandPalette.module.css'

export type { CommandItem } from './CommandPalette.commands'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
  onSelectView: (view: 'data' | 'empirical' | 'model' | 'methods') => void
  onSelectEmpiricalTab?: (tab: EmpiricalResultTab) => void
  onLoadDemo?: () => void
  variables?: Array<{ id: string; label: string }>
}

export function CommandPalette({
  isOpen,
  onClose,
  onSelectView,
  onSelectEmpiricalTab,
  onLoadDemo,
  variables = [],
}: CommandPaletteProps) {
  const [query, setQuery] = useState('')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const commands = useMemo<CommandItem[]>(
    () => buildCommandPaletteCommands({
      onSelectView,
      onSelectEmpiricalTab,
      onLoadDemo,
      variables,
      onClose,
    }),
    [onSelectView, onSelectEmpiricalTab, onLoadDemo, variables, onClose],
  )

  const filteredCommands = useMemo(() => {
    if (!query.trim()) return commands
    const q = query.toLowerCase()
    return commands.filter(
      (cmd) =>
        cmd.title.toLowerCase().includes(q) ||
        Boolean(cmd.subtitle?.toLowerCase().includes(q)),
    )
  }, [commands, query])

  const previousActiveElement = useRef<HTMLElement | null>(null)

  useEffect(() => {
    if (!isOpen) return
    previousActiveElement.current = document.activeElement as HTMLElement
    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    if (inputRef.current) {
      inputRef.current.focus()
    }

    return () => {
      document.body.style.overflow = originalOverflow
      if (previousActiveElement.current && typeof previousActiveElement.current.focus === 'function') {
        setTimeout(() => {
          previousActiveElement.current?.focus()
        }, 0)
      }
    }
  }, [isOpen])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelectedIndex((idx) => (idx + 1) % Math.max(1, filteredCommands.length))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelectedIndex((idx) => (idx - 1 + filteredCommands.length) % Math.max(1, filteredCommands.length))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const selected = filteredCommands[selectedIndex]
        if (selected) selected.action()
      } else if (e.key === 'Tab') {
        e.preventDefault()
        if (inputRef.current) inputRef.current.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, selectedIndex, filteredCommands, onClose])

  if (!isOpen) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="command-palette-heading"
      tabIndex={-1}
      className={styles.overlay}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose()
      }}
    >
      <div className={styles.panel}>
        <h2 id="command-palette-heading" className="sr-only">快捷指令与全局搜索</h2>
        <div className={styles.searchRow}>
          <SearchIcon size={18} className={styles.searchIcon} aria-hidden="true" />
          <input
            ref={inputRef}
            id="command-palette-search-input"
            type="text"
            role="combobox"
            aria-autocomplete="list"
            aria-expanded={isOpen}
            aria-controls="command-palette-listbox"
            aria-activedescendant={
              filteredCommands[selectedIndex]
                ? `cmd-option-${filteredCommands[selectedIndex].id}`
                : undefined
            }
            aria-label="搜索工作区、分析分区、变量或快捷指令"
            placeholder="搜索工作区、分析分区、变量或快捷指令 (Esc 退出)..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setSelectedIndex(0)
            }}
            className={styles.searchInput}
          />
          <kbd className={styles.kbd}>
            ESC
          </kbd>
        </div>

        <div
          id="command-palette-listbox"
          role="listbox"
          aria-label="快捷指令建议列表"
          className={styles.listbox}
        >
          {filteredCommands.length === 0 ? (
            <div className={styles.emptyState}>
              未找到匹配的命令或变量
            </div>
          ) : (
            filteredCommands.map((cmd, idx) => {
              const isSelected = idx === selectedIndex
              return (
                <button
                  type="button"
                  role="option"
                  id={`cmd-option-${cmd.id}`}
                  aria-selected={isSelected}
                  key={cmd.id}
                  className={`${styles.option} ${isSelected ? styles.optionSelected : ''}`}
                  onClick={() => cmd.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <span className={styles.optionIcon}>{cmd.icon}</span>
                  <div className={styles.optionContent}>
                    <span className={`${styles.optionTitle} ${isSelected ? styles.optionTitleSelected : ''}`}>
                      {cmd.title}
                    </span>
                    {cmd.subtitle ? (
                      <span className={styles.optionSubtitle}>{cmd.subtitle}</span>
                    ) : null}
                  </div>
                  {isSelected ? (
                    <span className={styles.executeHint}>↵ 执行</span>
                  ) : null}
                </button>
              )
            })
          )}
        </div>

        <div className={styles.footer}>
          <span>提示: 使用 ↑ ↓ 方向键选择，Enter 键执行</span>
          <span>研径 ResearchPath Command Palette</span>
        </div>
      </div>
    </div>
  )
}
