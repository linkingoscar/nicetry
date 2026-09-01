import type { Page } from '@playwright/test'

/**
 * Each E2E page receives the same session token after one capability exchange.
 * Global setup performs the production single-use exchange once so Playwright
 * worker restarts cannot accidentally consume the bootstrap capability again.
 */
export async function openAuthenticatedPage(page: Page): Promise<void> {
  const token = process.env.RESEARCHPATH_E2E_SESSION_TOKEN
  if (!token) {
    throw new Error('E2E 会话令牌未由 global setup 初始化')
  }
  await page.addInitScript(
    (sessionToken: string) => window.sessionStorage.setItem('researchpath.sessionToken', sessionToken),
    token,
  )
  await page.goto('/')
}
