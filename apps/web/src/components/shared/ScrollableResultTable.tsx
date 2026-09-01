import type { ReactNode } from 'react'

export function ScrollableResultTable({ label, children, className = 'table-wrap' }: { label: string; children: ReactNode; className?: string }) {
  return (
    // biome-ignore lint/a11y/noNoninteractiveTabindex: A horizontally scrollable viewport needs keyboard focus (WCAG 2.1.1); it is a named region, not a button.
    <section className={className} aria-label={label} tabIndex={0}>{children}</section>
  )
}
