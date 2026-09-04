import { expect, type Dialog, type Page } from '@playwright/test'

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

export async function openDataWorkspace(page: Page): Promise<void> {
  await openAuthenticatedPage(page)
  await expect(page.getByRole('heading', { name: '本地点按式实证分析工作台' })).toBeVisible()
  await page.getByRole('button', { name: /导入数据并开始分析/ }).click()
  await expect(page.getByRole('tab', { name: '数据', exact: true })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByRole('heading', { name: /^导入.+数据$/ })).toBeVisible()
}

export async function openAnalysisLibrary(page: Page): Promise<void> {
  await page.getByRole('tab', { name: '分析', exact: true }).click()
  await expect(page.getByRole('heading', { name: '分析方法', exact: true })).toBeVisible()
}

export async function configureMethod(
  page: Page,
  label: string,
  acceptDialog?: boolean,
): Promise<void> {
  await openAnalysisLibrary(page)
  if (acceptDialog !== undefined) {
    page.once('dialog', dialog => acceptDialog ? dialog.accept() : dialog.dismiss())
  }
  await page.getByRole('button', { name: `配置${label}`, exact: true }).click()
}

export async function openAdvancedProcessEditor(
  page: Page,
  label = '简单中介（PROCESS Model 4）',
): Promise<void> {
  await configureMethod(page, label)
  await page.getByRole('button', { name: '打开高级编辑器', exact: true }).click()
}

export async function openAdvancedSemEditor(page: Page): Promise<void> {
  await openAnalysisLibrary(page)
  const acceptEngineSwitch = (dialog: Dialog) => {
    void dialog.accept()
  }
  page.on('dialog', acceptEngineSwitch)
  const openAdvanced = page.getByRole('button', { name: '打开高级 SEM 编辑器', exact: true })
  try {
    await page.getByRole('button', { name: '配置结构方程模型（SEM）', exact: true }).click()
    await expect(openAdvanced).toBeVisible()
  } finally {
    page.off('dialog', acceptEngineSwitch)
  }
  await openAdvanced.click()
}
