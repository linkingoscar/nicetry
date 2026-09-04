import { expect, type Dialog, type Locator, type Page } from '@playwright/test'

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

async function anyVisible(locator: Locator): Promise<boolean> {
  const count = await locator.count()
  for (let index = 0; index < count; index += 1) {
    if (await locator.nth(index).isVisible()) return true
  }
  return false
}

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
  const methodButton = page.getByRole('button', { name: `配置${label}`, exact: true })
  const handleMethodDialog = (dialog: Dialog) => {
    void (acceptDialog === false ? dialog.dismiss() : dialog.accept())
  }
  page.on('dialog', handleMethodDialog)
  try {
    await methodButton.click()
    await expect(methodButton).toBeHidden()
    const completionText = acceptDialog === false
      ? /已取消目录方法切换/
      : new RegExp(`已进入(?:：|“)?${escapeRegExp(label)}`)
    await expect.poll(async () => (
      await anyVisible(page.getByText(completionText))
      || await anyVisible(page.getByRole('heading', { name: label, exact: true }))
    ), { timeout: 15_000 }).toBe(true)
  } finally {
    page.off('dialog', handleMethodDialog)
  }
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
