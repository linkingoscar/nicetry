import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it } from 'vitest'
import { LocalPrivacyBadge } from './LocalPrivacyBadge'

it('never substitutes a fabricated file digest for a missing one', async () => {
  const { rerender } = render(<LocalPrivacyBadge datasetName="example.csv" />)
  await userEvent.click(screen.getByRole('button', { name: /本机处理/ }))
  expect(screen.getByText('未提供')).toBeVisible()
  rerender(<LocalPrivacyBadge datasetName="example.csv" datasetSha256={'a'.repeat(64)} />)
  expect(screen.queryByText('未提供')).not.toBeInTheDocument()
  expect(screen.getByText(`${'a'.repeat(20)}…`)).toBeVisible()
})
