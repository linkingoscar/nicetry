import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { describe, expect, it } from 'vitest'
import { CommandPalette } from './CommandPalette'
import { EmpiricalResultsNav, type EmpiricalResultTab } from '../empirical/EmpiricalResultsNav'

function TestTabsWrapper() {
  const [activeTab, setActiveTab] = useState<EmpiricalResultTab>('overview')
  const statusMap = {
    overview: 'available' as const,
    correlation: 'available' as const,
    measurement: 'available' as const,
    diary: 'available' as const,
  }
  return (
    <EmpiricalResultsNav
      activeTab={activeTab}
      pending={false}
      onChange={(tab) => setActiveTab(tab)}
      statusMap={statusMap}
    />
  )
}

describe('WAI-ARIA APG Accessibility Integration Regression Tests', () => {
  describe('CommandPalette APG Combobox & Listbox Pattern', () => {
    it('exposes ARIA combobox/listbox/option roles, aria-activedescendant and ArrowUp/Down navigation', async () => {
      const user = userEvent.setup()

      function PaletteTest() {
        const [isOpen, setIsOpen] = useState(false)
        return (
          <div>
            <button type="button" onClick={() => setIsOpen(true)}>
              打开 Command Palette
            </button>
            <CommandPalette
              isOpen={isOpen}
              onClose={() => setIsOpen(false)}
              onSelectView={() => setIsOpen(false)}
            />
          </div>
        )
      }

      render(<PaletteTest />)

      const triggerBtn = screen.getByRole('button', { name: '打开 Command Palette' })
      triggerBtn.focus()
      await user.click(triggerBtn)
      await new Promise((resolve) => setTimeout(resolve, 20))

      // 1. Combobox & Listbox roles
      const combobox = screen.getByRole('combobox')
      const listbox = screen.getByRole('listbox')

      expect(combobox).toHaveAttribute('aria-autocomplete', 'list')
      expect(combobox).toHaveAttribute('aria-expanded', 'true')
      expect(combobox).toHaveAttribute('aria-controls', 'command-palette-listbox')
      expect(listbox).toBeInTheDocument()

      // 2. Active descendant option tracking via ArrowDown
      const options = screen.getAllByRole('option')
      expect(options[0]).toHaveAttribute('aria-selected', 'true')
      expect(combobox).toHaveAttribute('aria-activedescendant', options[0].id)

      // ArrowDown to 2nd option
      await user.keyboard('{ArrowDown}')
      expect(options[1]).toHaveAttribute('aria-selected', 'true')
      expect(combobox).toHaveAttribute('aria-activedescendant', options[1].id)

      // ArrowUp back to 1st option
      await user.keyboard('{ArrowUp}')
      expect(options[0]).toHaveAttribute('aria-selected', 'true')
      expect(combobox).toHaveAttribute('aria-activedescendant', options[0].id)

      // Press Esc to close & restore focus
      await user.keyboard('{Escape}')
      await new Promise((resolve) => setTimeout(resolve, 20))
      expect(document.activeElement).toBe(triggerBtn)
    })
  })

  describe('EmpiricalResultsNav APG Tabs Automatic Activation Pattern', () => {
    it('implements Automatic Activation (ArrowRight changes focus AND active selection state immediately)', async () => {
      const user = userEvent.setup()
      render(<TestTabsWrapper />)

      const overviewTab = screen.getByRole('tab', { name: /描述与正态性/i })
      const correlationTab = screen.getByRole('tab', { name: /相关与矩阵/i })

      // Initial state: Overview selected
      expect(overviewTab).toHaveAttribute('aria-selected', 'true')
      expect(overviewTab).toHaveAttribute('tabindex', '0')

      overviewTab.focus()
      expect(document.activeElement).toBe(overviewTab)

      // ArrowRight -> Immediately activates Correlation tab (Automatic Activation)
      await user.keyboard('{ArrowRight}')

      expect(correlationTab).toHaveAttribute('aria-selected', 'true')
      expect(correlationTab).toHaveAttribute('tabindex', '0')
      expect(overviewTab).toHaveAttribute('aria-selected', 'false')
      expect(overviewTab).toHaveAttribute('tabindex', '-1')
      expect(document.activeElement).toBe(correlationTab)
    })
  })
})
